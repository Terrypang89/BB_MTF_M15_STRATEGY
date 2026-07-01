#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "36.10"
//+------------------------------------------------------------------+
//| TofyTrade6 — DualTF Stack logic                                   |
//| Part 3 (IDENTIFY) + per-TF BBLoc + LOGGING + Part 4 PREDICTION.  |
//| Part 4 = ported from analyze_multiinput_prediction.py (Predictor A) |
//| Prediction computed/logged/drawn for DIAGNOSIS only — NO trading. |
//| Per-TF BBLoc format: HTF=F3F5 MTF=F3F5 LTF=F3                     |
//| NOTE: 43.9% accuracy measured on OLD H1-predict/M30-verify logic. |
//|  After M30-consistency fix, accuracy must be RE-MEASURED.          |
//| Repo logic file, sibling to TofyTrade5.mqh —                      |
//| user integrates/compiles/backtests locally.                       |
//| Separate from the 7-scenario system.                              |
//+------------------------------------------------------------------+
#include <TofyIncludeSimple.mqh>

//═══════════════════════════════════════════════════════════════════
// SIG LOGGING — same grammar as TofyTrade5 (colon-separated KV)
//═══════════════════════════════════════════════════════════════════
string KV6(string k, string v)             { return " "+k+":"+v; }
string KVi6(string k, int v)               { return " "+k+":"+IntegerToString(v); }
string KVd6(string k, double v, int dp=2)  { return " "+k+":"+DoubleToString(v,dp); }

void SigEvt6(string evt, string kvs)
{  Print("[DUALTF] SIG:DUALTF", KV6("evt",evt), kvs); }

//═══════════════════════════════════════════════════════════════════
// ENUM — 4-state per TF
//═══════════════════════════════════════════════════════════════════
enum DUAL_STATE { DS_F=0, DS_S=1, DS_C=2, DS_R=3, DS_X=4 }; // Fly-up, Shrink, Compress, Fly-down, No-data

string DualStateName(DUAL_STATE d) {
   switch(d){
      case DS_F: return "F";
      case DS_S: return "S";
      case DS_C: return "C";
      case DS_R: return "R";
      case DS_X: return "X";
      default:   return "?";
   }
}

//═══════════════════════════════════════════════════════════════════
// STRUCT — DualTFScenarioState  (design doc §3.1)
//═══════════════════════════════════════════════════════════════════
struct DualTFScenarioState {
   string htf_scenario;       // 2-char: (D1-state)(H4-state), e.g. "FS"
   string mtf_scenario;       // 2-char: (H1-state)(M30-state), e.g. "FC"
   int    htf_bbloc;          // 0-10, real price-vs-D1-band (legacy, kept for compat)
   int    mtf_bbloc;          // sparse, real price-vs-H1-band (legacy, kept for compat)
   //--- Per-TF BBLoc (V36.05): each TF from its own bands
   // SCALE: HTF pair (D1,H4) = full 0-10; MTF+LTF (H1,M30,M15) = sparse {0,1,3,5,7,9,10}
   // Anchors align (1=lower,5=mid,9=upper) so "3" means low-mid on all.
   // OPTION: if user prefers ALL 0-10, swap ComputeMTFBBLoc → ComputeHTFBBLoc per-TF below.
   int    d1_bbloc;           // 0-10, from D1 bands
   int    h4_bbloc;           // 0-10, from H4 bands
   int    h1_bbloc;           // sparse, from H1 bands
   int    m30_bbloc;          // sparse, from M30 bands
   int    m15_bbloc;          // sparse, from M15 bands
   //--- Paired combo strings (V36.05): HTF=F3F5, MTF=F3F5, LTF=F3
   string htf_combo;          // e.g. "F3F5" (D1-fly@3, H4-fly@5)
   string mtf_combo;          // e.g. "F3F5" (H1-fly@3, M30-fly@5)
   string ltf_combo;          // e.g. "F3"   (M15-fly@3)
   string htf_d1_state;       // "F"/"S"/"C"/"R"
   string htf_h4_state;       // "F"/"S"/"C"/"R"
   string mtf_h1_state;       // "F"/"S"/"C"/"R"
   string mtf_m30_state;      // "F"/"S"/"C"/"R"
   string m15_state;          // "F"/"S"/"C"/"R" — leading edge
   string info;               // human-readable reason string
};

//═══════════════════════════════════════════════════════════════════
// PER-TF F/S/C/R DERIVATION
//═══════════════════════════════════════════════════════════════════
// 511/512 -> F, 521/522 -> R, 513/523 -> S, 400-499 -> C
DUAL_STATE BBStageToDualState(int stage)
{
   if(stage==0)                return DS_X;   // no data — flag explicitly, don't fake
   if(stage==511 || stage==512) return DS_F;
   if(stage==521 || stage==522) return DS_R;
   if(stage==513 || stage==523) return DS_S;
   if(stage>=400 && stage<500)  return DS_C;
   return DS_S;   // fallback — unknown stage treated as shrink
}

//═══════════════════════════════════════════════════════════════════
// REAL BBLOC COMPUTATION  (design doc §3.4)
//═══════════════════════════════════════════════════════════════════
// Core: ratio = (price - BBLowLV) / (BBUppLV - BBLowLV)
//        bbloc_raw = ratio * 10, clamped 0-10
// HTF (D1/H4): round to 0-10 (full resolution)
// MTF (H1/M30): snap to nearest of {0,1,3,5,7,9,10}

//--- raw ratio -> 0-10 (clamped, outside-band handled)
double ComputeBBLocRaw(double price, double bblow, double bbupp)
{
   double width = bbupp - bblow;
   if(width <= 0.0) return -1.0;  // degenerate/missing bands -> no-data sentinel
   double ratio = (price - bblow) / width;
   double raw   = ratio * 10.0;
   if(raw < 0.0)  raw = 0.0;      // below lower band -> 0
   if(raw > 10.0) raw = 10.0;     // above upper band -> 10
   return raw;
}

//--- HTF: round to 0-10 (full resolution)
int ComputeHTFBBLoc(double price, double bblow, double bbupp)
{
   double raw = ComputeBBLocRaw(price, bblow, bbupp);
   return (int)MathRound(raw);
}

//--- MTF: snap to nearest of {0,1,3,5,7,9,10}
int SnapToMTFScale(double raw)
{
   int scale[] = {0,1,3,5,7,9,10};
   int best = 5;
   double bestDist = 999.0;
   for(int i=0; i<ArraySize(scale); i++) {
      double d = MathAbs(raw - scale[i]);
      if(d < bestDist) { bestDist = d; best = scale[i]; }
   }
   return best;
}

int ComputeMTFBBLoc(double price, double bblow, double bbupp)
{
   double raw = ComputeBBLocRaw(price, bblow, bbupp);
   if(raw < 0.0) return -1;   // no-data sentinel — don't snap
   return SnapToMTFScale(raw);
}

//--- Helper: format a single {state}{bbloc} segment for combo strings
// No-data (bbloc == -1) → "X-" so the absence is obvious, e.g. "F3X-F5"
string ComboSegment(string state, int bbloc)
{
   if(bbloc < 0) return "X-";
   return state + IntegerToString(bbloc);
}

//═══════════════════════════════════════════════════════════════════
// ROLLING M30_BBLOC BUFFER + SLOPE — for Part 4 prediction
// V36.06: uses M30 bbloc (m30_bbloc) — prediction + verification both M30
// Ported from analyze_multiinput_prediction.py — Predictor A
// 43.9% stale (measured on H1-predict/M30-verify mismatch) — must re-measure
//═══════════════════════════════════════════════════════════════════
#define BBLoc_BUF_SIZE  6   // last 6 bars of mtf_bbloc

//--- rolling buffer of recent mtf_bbloc values
static int  s_bblocBuf[BBLoc_BUF_SIZE];   // circular buffer
static int  s_bblocBufIdx = 0;            // next write position
static bool s_bblocBufReady = false;      // true after BBLoc_BUF_SIZE fills

void UpdateBBLocBuf(int bbloc)
{
   s_bblocBuf[s_bblocBufIdx] = bbloc;
   s_bblocBufIdx = (s_bblocBufIdx + 1) % BBLoc_BUF_SIZE;
   if(s_bblocBufIdx == 0)
      s_bblocBufReady = true;   // buffer has been written at least once fully
}

//--- linear regression slope (same math as Python bbloc_slope)
// Skips -1 (no-data) values — they don't corrupt the slope
double ComputeBBLocSlope()
{
   // Collect valid (non -1) values into a temp array
   double valid[];
   int    validCount = 0;
   for(int i = 0; i < BBLoc_BUF_SIZE; i++)
   {
      if(s_bblocBuf[i] >= 0)
      {
         validCount++;
         ArrayResize(valid, validCount);
         valid[validCount - 1] = (double)s_bblocBuf[i];
      }
   }
   if(validCount < 2) return 0.0;   // not enough data

   // Linear regression: slope = sum((x-xm)(y-ym)) / sum((x-xm)^2)
   double xMean = (validCount - 1) / 2.0;
   double yMean = 0.0;
   for(int i = 0; i < validCount; i++)
      yMean += valid[i];
   yMean /= validCount;

   double num = 0.0, den = 0.0;
   for(int i = 0; i < validCount; i++)
   {
      double xDiff = (double)i - xMean;
      num += xDiff * (valid[i] - yMean);
      den += xDiff * xDiff;
   }
   if(den == 0.0) return 0.0;
   return num / den;
}

//═══════════════════════════════════════════════════════════════════
// IDENTIFY DUALTF — Part 3, Layer 1
//═══════════════════════════════════════════════════════════════════
// Reads BB_datas[] + price -> per-TF F/S/C/R -> HTF/MTF pairs ->
// real BBLoc -> fills and returns DualTFScenarioState.
// TF index convention (same as TofyTrade5):
//   0=M5, 1=M15, 2=M30, 3=H1, 4=H4, 5=D1
DualTFScenarioState IdentifyDualTF(BB_MTF_Data_struct &bb[], double &close_prices[])
{
   DualTFScenarioState s;
   s.htf_scenario=""; s.mtf_scenario="";
   s.htf_bbloc=5; s.mtf_bbloc=5;
   s.d1_bbloc=5; s.h4_bbloc=5; s.h1_bbloc=5; s.m30_bbloc=5; s.m15_bbloc=5;
   s.htf_combo=""; s.mtf_combo=""; s.ltf_combo="";
   s.htf_d1_state="S"; s.htf_h4_state="S";
   s.mtf_h1_state="S"; s.mtf_m30_state="S";
   s.m15_state="S";
   s.info="";

   double price = close_prices[LA];

   //--- Per-TF F/S/C/R derivation
   DUAL_STATE d1_st  = BBStageToDualState((int)bb[5].BBW_stage[LA]);
   DUAL_STATE h4_st  = BBStageToDualState((int)bb[4].BBW_stage[LA]);
   DUAL_STATE h1_st  = BBStageToDualState((int)bb[3].BBW_stage[LA]);
   DUAL_STATE m30_st = BBStageToDualState((int)bb[2].BBW_stage[LA]);
   DUAL_STATE m15_st = BBStageToDualState((int)bb[1].BBW_stage[LA]);

   //--- Store per-TF state strings
   s.htf_d1_state   = DualStateName(d1_st);
   s.htf_h4_state   = DualStateName(h4_st);
   s.mtf_h1_state   = DualStateName(h1_st);
   s.mtf_m30_state  = DualStateName(m30_st);
   s.m15_state      = DualStateName(m15_st);

   //--- HTF scenario pair: (D1-state)(H4-state)
   s.htf_scenario = s.htf_d1_state + s.htf_h4_state;

   //--- MTF scenario pair: (H1-state)(M30-state)
   s.mtf_scenario = s.mtf_h1_state + s.mtf_m30_state;

   //--- Per-TF BBLoc — each TF from its own bands (V36.05)
   // HTF axis (D1, H4): full 0-10 resolution
   s.d1_bbloc = ComputeHTFBBLoc(price, bb[5].BBLowLV[LA], bb[5].BBUppLV[LA]);
   s.h4_bbloc = ComputeHTFBBLoc(price, bb[4].BBLowLV[LA], bb[4].BBUppLV[LA]);
   // MTF+LTF axis (H1, M30, M15): sparse {0,1,3,5,7,9,10}
   s.h1_bbloc  = ComputeMTFBBLoc(price, bb[3].BBLowLV[LA], bb[3].BBUppLV[LA]);
   s.m30_bbloc = ComputeMTFBBLoc(price, bb[2].BBLowLV[LA], bb[2].BBUppLV[LA]);
   s.m15_bbloc = ComputeMTFBBLoc(price, bb[1].BBLowLV[LA], bb[1].BBUppLV[LA]);

   //--- Legacy aliases (kept for backward compat)
   s.htf_bbloc = s.d1_bbloc;
   s.mtf_bbloc = s.h1_bbloc;

   //--- No-data gate: TF state == "X" → that TF's bbloc = -1
   if(s.htf_d1_state == "X") s.d1_bbloc = -1;
   if(s.htf_h4_state == "X") s.h4_bbloc = -1;
   if(s.mtf_h1_state == "X") s.h1_bbloc = -1;
   if(s.mtf_m30_state == "X") s.m30_bbloc = -1;
   if(s.m15_state == "X") s.m15_bbloc = -1;

   //--- Build paired combo strings (V36.05): HTF=D1+H4, MTF=H1+M30, LTF=M15
   // No-data shown as "X-", e.g. "F3X-F5" if D1 bbloc is -1
   s.htf_combo = ComboSegment(s.htf_d1_state, s.d1_bbloc) +
                 ComboSegment(s.htf_h4_state, s.h4_bbloc);
   s.mtf_combo = ComboSegment(s.mtf_h1_state, s.h1_bbloc) +
                 ComboSegment(s.mtf_m30_state, s.m30_bbloc);
   s.ltf_combo = ComboSegment(s.m15_state, s.m15_bbloc);

   //--- Info string (updated to show per-TF combos)
   s.info = "HTF="+s.htf_combo+" MTF="+s.mtf_combo+" LTF="+s.ltf_combo;

   return s;
}

//═══════════════════════════════════════════════════════════════════
// PART 4 — PREDICTION STRUCT (forward, detailed impl below)
//═══════════════════════════════════════════════════════════════════
struct MTFPrediction {
   string pred_direction;       // "up" / "down" / "neutral"
   string predicted_mtf;        // predicted next MTF scenario (2-char)
   int    predicted_bbloc;      // predicted next MTF BBLoc
   double bbloc_slope;          // slope of mtf_bbloc over last 6 bars
   string hit_miss;             // "HIT" / "MISS" / "NA"
};

//═══════════════════════════════════════════════════════════════════
// LOGGING — per-bar, parseable (the redesign dataset)
//═══════════════════════════════════════════════════════════════════
// Log format (colon-separated, no spaces in values):
// [DUALTF] SIG:DUALTF evt:BAR dt:<datetime>
//   d1:stg:<BBW_stage> mid:<diffMid> ud:<BBUpDn> state:<F/S/C/R> bbloc:<N>
//   h4:stg:<...> mid:<...> ud:<...> state:<...> bbloc:<N>
//   h1:stg:<...> mid:<...> ud:<...> state:<...> bbloc:<N>
//   m30:stg:<...> mid:<...> ud:<...> state:<...> bbloc:<N>
//   m15:stg:<...> mid:<...> ud:<...> state:<...> bbloc:<N>
//   htf:<scenario> mtf:<scenario>
//   htfcombo:<F3F5> mtfcombo:<F3F5> ltfcombo:<F3>
//   pred:<up/down/neutral> predmtf:<predicted_MTF> predbbloc:<N> slope:<bbloc_slope> predhit:<HIT/MISS/NA>

void LogDualTFBar(BB_MTF_Data_struct &bb[], DualTFScenarioState &s, const MTFPrediction &pred)
{
   datetime dt = iTime(_Symbol, PERIOD_M5, 0);
   string dtStr = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   string kvs =
      KV6("dt", dtStr)
      +KV6("d1:stg", IntegerToString((int)bb[5].BBW_stage[LA]))
      +KV6("d1:mid", IntegerToString(bb[5].BB_diffMid_Trend[LA]))
      +KV6("d1:ud",  IntegerToString(bb[5].BBUpDn_state[LA]))
      +KV6("d1:state", s.htf_d1_state)
      +KVi6("d1bbloc", s.d1_bbloc)
      +KV6("h4:stg", IntegerToString((int)bb[4].BBW_stage[LA]))
      +KV6("h4:mid", IntegerToString(bb[4].BB_diffMid_Trend[LA]))
      +KV6("h4:ud",  IntegerToString(bb[4].BBUpDn_state[LA]))
      +KV6("h4:state", s.htf_h4_state)
      +KVi6("h4bbloc", s.h4_bbloc)
      +KV6("h1:stg", IntegerToString((int)bb[3].BBW_stage[LA]))
      +KV6("h1:mid", IntegerToString(bb[3].BB_diffMid_Trend[LA]))
      +KV6("h1:ud",  IntegerToString(bb[3].BBUpDn_state[LA]))
      +KV6("h1:state", s.mtf_h1_state)
      +KVi6("h1bbloc", s.h1_bbloc)
      +KV6("m30:stg", IntegerToString((int)bb[2].BBW_stage[LA]))
      +KV6("m30:mid", IntegerToString(bb[2].BB_diffMid_Trend[LA]))
      +KV6("m30:ud",  IntegerToString(bb[2].BBUpDn_state[LA]))
      +KV6("m30:state", s.mtf_m30_state)
      +KVi6("m30bbloc", s.m30_bbloc)
      +KV6("m15:stg", IntegerToString((int)bb[1].BBW_stage[LA]))
      +KV6("m15:mid", IntegerToString(bb[1].BB_diffMid_Trend[LA]))
      +KV6("m15:ud",  IntegerToString(bb[1].BBUpDn_state[LA]))
      +KV6("m15:state", s.m15_state)
      +KVi6("m15bbloc", s.m15_bbloc)
      +KV6("htf", s.htf_scenario)
      +KV6("mtf", s.mtf_scenario)
      //--- Per-TF combo strings (V36.05)
      +KV6("htfcombo", s.htf_combo)
      +KV6("mtfcombo", s.mtf_combo)
      +KV6("ltfcombo", s.ltf_combo)
      //--- Part 4 prediction fields (diagnosis only, 43.9% stale — see V36.06 note)
      +KV6("pred", pred.pred_direction)
      +KV6("predmtf", pred.predicted_mtf)
      +KVi6("predbbloc", pred.predicted_bbloc)
      +KV6("slope", DoubleToString(pred.bbloc_slope, 2))
      +KV6("predhit", pred.hit_miss);

   SigEvt6("BAR", kvs);
}

//═══════════════════════════════════════════════════════════════════
// DRAW LABEL — V36.09: DIAGNOSTIC — direct ObjectCreate, bypasses DRAW_LABEL
//═══════════════════════════════════════════════════════════════════
// Diagnostic build: bypasses DRAW_LABEL (EA include, unreadable) and creates
// the label object directly. Hardcoded fontsize 10 + white. Logs [LABELDBG] with
// creation result, error code, price, time, M30 font size, and tag.
// One backtest + reading the [LABELDBG] lines reveals why labels don't appear.
void DrawGateLabel(string tag, double price, BB_MTF_Data_struct &BB_datas[],
                   color labelColor, int tf_idx=1)
{
   datetime curtime = iTime(_Symbol, PERIOD_M5, 0);
   string nm = "DTF_" + IntegerToString((int)curtime);
   ResetLastError();
   bool created = ObjectCreate(0, nm, OBJ_TEXT, 0, curtime, price);
   int errAfterCreate = GetLastError();
   ObjectSetString(0, nm, OBJPROP_TEXT, tag);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, 10);     // hardcoded visible size
   ObjectSetInteger(0, nm, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT);
   ObjectSetInteger(0, nm, OBJPROP_ANGLE, 90);   // vertical, bottom-to-top
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   Print("[LABELDBG] created=", created, " name=", nm,
         " err=", errAfterCreate, " price=", DoubleToString(price,2),
         " curtime=", TimeToString(curtime, TIME_DATE|TIME_MINUTES),
         " fontsrc_bb2=", BB_datas[tf_idx].BBFontSize,
         " tag=", tag);
}

//═══════════════════════════════════════════════════════════════════
// PART 4 — REAL PREDICTION (ported from analyze_multiinput_prediction.py)
//
// Predictor A: BBLoc slope only — DIAGNOSIS only, NOT VIABLE.
// V36.06: prediction + verification both target M30 (2nd char of MTF)
//   — consistent. The old H1-predicts/M30-verifies mismatch is fixed.
//   The 43.9% accuracy was measured on the OLD inconsistent version and
//   no longer applies until the analysis script is re-run on this logic.
//
// Logic (from predict_bbloc_only in analyze_multiinput_prediction.py):
//   bbloc_slope over last 6 bars of M30 bbloc (linear regression, same as Python).
//   slope >  0.3 → predict "up"     (up-continuation transition)
//   slope < -0.3 → predict "down"   (down-reversal transition)
//   |slope| <= 0.3 → predict "neutral" (persist — no transition)
//
// Direction comparison (from classify_transition_direction):
//   Order: R(0) < S(1) < F(2) < C(3) — second letter of MTF scenario.
//   If TO second-letter value > FROM → "up"; < → "down"; == → "neutral".
//═══════════════════════════════════════════════════════════════════
//--- Map predicted direction to a concrete MTF scenario
// "up" → second letter advances toward C (R→S, S→F, F→C)
// "down" → second letter recedes toward R (C→F, F→S, S→R)
// "neutral" → same scenario (persist)
static string DirectionLetterMap[4] = {"R","S","F","C"}; // index 0=R,1=S,2=F,3=C

//--- Static to store previous bar's predicted direction (for hit/miss)
static string s_predDirection = "";   // last bar's predicted direction
static string s_prevMtfScenario = ""; // last bar's MTF scenario

string AdvanceSecondLetter(string curLetter, string direction)
{
   int curIdx = -1;
   for(int i = 0; i < 4; i++)
   {
      if(DirectionLetterMap[i] == curLetter) { curIdx = i; break; }
   }
   if(curIdx < 0) return curLetter; // unknown, keep
   if(direction == "up" && curIdx < 3)
      return DirectionLetterMap[curIdx + 1];
   if(direction == "down" && curIdx > 0)
      return DirectionLetterMap[curIdx - 1];
   return curLetter; // neutral or at boundary
}

//--- Classify the actual transition direction (same as Python)
string ClassifyActualDirection(string fromMtf, string toMtf)
{
   if(fromMtf == toMtf) return "neutral";
   if(StringLen(fromMtf) < 2 || StringLen(toMtf) < 2) return "neutral";
   string fromCh = StringSubstr(fromMtf, 1, 1);
   string toCh   = StringSubstr(toMtf, 1, 1);
   int fromVal = -1, toVal = -1;
   for(int i = 0; i < 4; i++)
   {
      if(DirectionLetterMap[i] == fromCh) fromVal = i;
      if(DirectionLetterMap[i] == toCh)   toVal   = i;
   }
   if(fromVal < 0 || toVal < 0) return "neutral";
   if(toVal > fromVal)  return "up";
   if(toVal < fromVal)  return "down";
   return "neutral";
}

//--- Main prediction function — ported from analyze_multiinput_prediction.py
// Also performs one-bar-delayed hit/miss check against actual transition
MTFPrediction PredictNextMTF(DualTFScenarioState &s, string prevMtfScenario)
{
   MTFPrediction p;
   p.bbloc_slope    = 0.0;
   p.pred_direction = "neutral";
   p.predicted_mtf  = s.mtf_scenario;
   p.predicted_bbloc = s.m30_bbloc;
   p.hit_miss       = "NA";

   //--- No-data guard (M30 — consistent with prediction target)
   if(s.m30_bbloc < 0)
   {
      p.pred_direction = "neutral";
      p.hit_miss       = "NA";
      return p;
   }

   //--- Compute slope from rolling buffer (same as Python bbloc_slope)
   p.bbloc_slope = ComputeBBLocSlope();

   //--- Prediction rule (same thresholds as Python: predict_bbloc_only)
   if(p.bbloc_slope > 0.3)
      p.pred_direction = "up";
   else if(p.bbloc_slope < -0.3)
      p.pred_direction = "down";
   else
      p.pred_direction = "neutral";

   //--- Map direction to predicted MTF scenario
   // APPROXIMATE — derived by shifting the M30 char (2nd letter) by the
   // predicted direction. Not a validated scenario predictor.
   if(p.pred_direction == "neutral")
   {
      p.predicted_mtf = s.mtf_scenario; // persist
   }
   else
   {
      string firstCh = StringSubstr(s.mtf_scenario, 0, 1); // H1 stays
      string secondCh = StringSubstr(s.mtf_scenario, 1, 1); // M30 shifts
      string nextSecond = AdvanceSecondLetter(secondCh, p.pred_direction);
      p.predicted_mtf = firstCh + nextSecond;
   }

   //--- Project predicted_bbloc from M30 bbloc + slope direction
   // APPROXIMATE — step the current m30_bbloc in the slope direction,
   // clamped to {0,1,3,5,7,9,10} sparse scale. Not a validated predictor.
   if(p.pred_direction == "up" && s.m30_bbloc < 10)
      p.predicted_bbloc = MathMin(s.m30_bbloc + 2, 10);
   else if(p.pred_direction == "down" && s.m30_bbloc > 0)
      p.predicted_bbloc = MathMax(s.m30_bbloc - 2, 0);
   else
      p.predicted_bbloc = s.m30_bbloc;

   //--- One-bar-delayed hit/miss: compare previous bar's prediction to actual
   // prevMtfScenario = MTF scenario on the previous bar
   // s.mtf_scenario   = MTF scenario on the current bar (the "actual")
   if(prevMtfScenario != "" && prevMtfScenario != "XX" && s.mtf_scenario != "XX")
   {
      string actualDir = ClassifyActualDirection(prevMtfScenario, s.mtf_scenario);
      // We need the direction that was predicted on the previous bar.
      // This is tracked in s_predDirection (static, set after prediction each bar).
      if(s_predDirection != "")
      {
         if(s_predDirection == actualDir)
            p.hit_miss = "HIT";
         else
            p.hit_miss = "MISS";
      }
   }

   return p;
}

//═══════════════════════════════════════════════════════════════════
// TRADE STRATEGY — V36.06: identify + per-TF BBLoc + log + draw + predict
// Prediction + verification both M30 (consistent). DIAGNOSIS only — Trade_act = 0
// Signature matches TofyTrade5 exactly so the EA call site works unchanged.
//═══════════════════════════════════════════════════════════════════
void Trade_Strategy(
   BB_MTF_Data_struct      &BB_datas[],
   ATRSLBUF_struct         &ATRSL1BUF,
   BB_MTF_Impact_struct    &BBTFImpact,
   ENUM_Trade_Act          &Trade_act,   // OUT: 0=hold 1=exit_sell+buy 2=exit_buy+sell 7=exit_all
   string                  &Trade_info,
   double                  &Trade_lots,
   double                  &Trade_sl,
   int                      BUYS,
   int                      SELLS,
   double                  &close_prices[],
   double                   baseLot = 0.01
)
{
   //--- Defaults: HOLD, no stop, base lot
   Trade_act=0; Trade_info=""; Trade_lots=baseLot; Trade_sl=0.0;

   //--- Once-per-bar guard
   static datetime s_lastBar=0;
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur==s_lastBar) { Trade_info=""; return; }
   s_lastBar=cur;

   //--- Layer 1: Identify DualTF scenario + compute real BBLoc
   DualTFScenarioState s = IdentifyDualTF(BB_datas, close_prices);

   //--- Update rolling BBLoc buffer (for slope computation)
   // V36.06 FIX: use M30 bbloc — prediction + verification both target M30
   // (2nd char of MTF scenario). Old version used H1 bbloc (mtf_bbloc) which
   // created an H1-predicts/M30-verifies mismatch.
   UpdateBBLocBuf(s.m30_bbloc);

   //--- Part 4: Predict next MTF + one-bar-delayed hit/miss
   MTFPrediction pred = PredictNextMTF(s, s_prevMtfScenario);

   //--- Store this bar's prediction for next bar's hit/miss check
   s_predDirection   = pred.pred_direction;
   s_prevMtfScenario = s.mtf_scenario;

   //--- Log the per-bar DualTF data (produces the redesign dataset)
   LogDualTFBar(BB_datas, s, pred);

   //--- Draw chart label only on scenario CHANGE (readable chart)
   // Change key = the combo strings (HTF+MTF+LTF combos)
   static string s_prevScenario = "";
   string curKey = s.htf_combo + s.mtf_combo + s.ltf_combo;
   if(curKey != s_prevScenario) {
      s_prevScenario = curKey;
      // Build sanitized tag — valid MT5 object name chars only:
      // HTF-F3F5_MTF-F3F5_LTF-F3_PRED-down-FS3-MISS
      // ":"→"-", space→"_", "/"→"-", "[]"removed, slope dropped from chart
      string tag = "HTF-"+s.htf_combo+"_MTF-"+s.mtf_combo+"_LTF-"+s.ltf_combo+
                   "_PRED-"+pred.pred_direction+"-"+pred.predicted_mtf+
                   IntegerToString(pred.predicted_bbloc);
      if(pred.hit_miss != "NA")
         tag += "-"+pred.hit_miss;
      // M30 font size (bb[2] = M30 index). White only. DRAW_LABEL from EA includes.
      DrawGateLabel(tag, close_prices[LA], BB_datas, clrWhite, 2);
   }

   //--- Set Trade_info to the scenario summary
   Trade_info = s.info + " | PRED:" + pred.pred_direction +
                "/" + pred.predicted_mtf +
                "[" + IntegerToString(pred.predicted_bbloc) + "]" +
                " slope:" + DoubleToString(pred.bbloc_slope, 2) +
                " hit:" + pred.hit_miss;

   // V36.08: identify + per-TF BBLoc + log + draw + predict. NO trades —
   // prediction shown for DIAGNOSIS only. 43.9% stale, must re-measure.
}

//═══════════════════════════════════════════════════════════════════
// PART 5 — DEFERRED
//
// Trade action deferred. Part 4 prediction scored 43.9% OOS (not viable).
// No trade logic will be built on this prediction.
//═══════════════════════════════════════════════════════════════════
// TradeAction struct and DecideDualTFAction function — DEFERRED.
// See header comment: "Part 5 deferred stub."
//+------------------------------------------------------------------+
// INTEGRATION NOTES:
// 1. This file is a repo logic file — sibling to TofyTrade5.mqh.
//    User integrates into their EA locally; does not #include TofyTrade5.
// 2. BB_datas[] index convention: 0=M5, 1=M15, 2=M30, 3=H1, 4=H4, 5=D1.
// 3. Call Trade_Strategy() — same signature as TofyTrade5. It calls
//    IdentifyDualTF + PredictNextMTF + LogDualTFBar + DrawGateLabel.
// 4. Trade_Strategy returns Trade_act=0 (HOLD) — no trades. Prediction
//    shown for DIAGNOSIS only. 43.9% stale (V36.06 consistency fix).
// 5. Part 5 (trade action) is DEFERRED — no DecideDualTFAction yet.
// 6. V36.05: per-TF BBLoc — each TF from its own bands. HTF pair (D1,H4)
//    = full 0-10; MTF+LTF (H1,M30,M15) = sparse {0,1,3,5,7,9,10}.
//    OPTION: to use ALL 0-10, swap ComputeMTFBBLoc → ComputeHTFBBLoc
//    for H1/M30/M15 in IdentifyDualTF (3 lines).
// 7. Combo format: HTF={D1state}{D1bbloc}{H4state}{H4bbloc} e.g. "F3F5"
//    MTF={H1state}{H1bbloc}{M30state}{M30bbloc}, LTF={M15state}{M15bbloc}.
//    No-data shown as "X-", e.g. "F3X-F5" if D1 bbloc is -1.
// 8. DrawGateLabel uses M30 font size (bb[2]) for the chart label.
//    V36.08: sanitized tag passed directly to DRAW_LABEL (which handles
//    name + text internally). Tag format: HTF-F3F5_MTF-F3F5_LTF-F3_PRED-down-FS3-MISS.
//    Color always white. Depends on DRAW_LABEL macro from EA includes.
// 9. V36.08: prediction + verification both target M30 (consistent).
//    Rolling 6-bar M30 bbloc buffer + linear regression slope.
//    Thresholds: >0.3=up, <-0.3=down, else neutral.
//    predicted_mtf = H1-char + M30-char-shifted-by-direction (approximate).
//    predicted_bbloc = m30_bbloc stepped by slope direction (approximate).
//    One-bar-delayed hit/miss tracking — bar N predicts N+1, checked
//    at N+1. Log fields: pred, predmtf, predbbloc, slope, predhit.
//    All 5 fields shown in chart label.
//+------------------------------------------------------------------+
