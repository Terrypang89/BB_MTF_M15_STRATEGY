#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version "36.14"
//+------------------------------------------------------------------+
//| TofyTrade6 — DualTF Stack logic                                   |
//| V36.14 — M30-confirmed cascade entry.                              |
//|   Enters when M30 confirms the M15 flip direction within 12 bars, |
//|   instead of on M15-alone. Tests whether confirmed entry has a    |
//|   real dollar edge (cascade proxy showed +65pp WR but negative     |
//|   bbloc expectancy — only realized dollars decide).                |
//| V36.13 — EXIT-RETRY FIX: pos.open cleared only on confirmed-flat.  |
//|   exit_pending retry loop re-issues act=7 until broker closes.    |
//|   Fixes orphan bug (ERROR 4756, 2026.01.14).                      |
//|   V36.12: DIAGNOSTIC [EXITDBG] — removed (diagnostic complete).   |
//|   V36.11: FIRST TRADING VERSION — TransitionDetector + v1 ruleset.|
//|                                                                    |
//| PART 4 — TransitionDetector (M15 F/R flip detection)               |
//| PART 5 — v1 Trade Ruleset (gate, entry, TP, SL, invalidation)      |
//| Prediction fields (pred/predmtf/slope/predhit) = DIAGNOSTIC ONLY   |
//|   — NOT trade inputs.                                              |
//| Repo logic file, sibling to TofyTrade5.mqh —                       |
//| user integrates/compiles/backtests locally.                        |
//| Separate from the 7-scenario system.                               |
// M5 added to Part 3 LTF combo (observation only; not used in trade   |
// decisions).                                                            |
//+------------------------------------------------------------------+
//═══════════════════════════════════════════════════════════════════
// STEP 0 — ENUM_Trade_Act interface findings (from TofyTrade5.mqh):
//   0 = hold (no action)
//   1 = exit_sell+buy  (open BUY / switch to BUY)
//   2 = exit_buy+sell  (open SELL / switch to SELL)
//   7 = exit_all       (close all positions)
// Trade_sl = PRICE convention (confirmed: GetATRSLStop returns a price).
// BUYS/SELLS = open position counts; BUYS+SELLS==0 means flat.
// No TP parameter exists — TP managed in logic (monitor each bar).
//
// FLAG — SL handling: Trade_sl is set at entry. The EA/broker may
// execute the SL independently. SL_HIT detection is best-effort:
// if close_price <= SL (BUY) or >= SL (SELL) on an exit bar, we
// log SL_HIT. However, the EA may close the position before we
// see the bar (tick-level SL), so SL_HIT may be underreported.
// Verify at compile: does the EA apply Trade_sl via OrderSend
// or OrderModify? If so, SL is broker-managed and SL_HIT is
// broker-executed — we may never see the bar.
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
   int    m5_bbloc;          // sparse, from M15 bands
   //--- Paired combo strings (V36.05): HTF=F3F5, MTF=F3F5, LTF=F3
   string htf_combo;          // e.g. "F3F5" (D1-fly@3, H4-fly@5)
   string mtf_combo;          // e.g. "F3F5" (H1-fly@3, M30-fly@5)
   string ltf_combo;          // e.g. "F3"   (M15-fly@3)
   string htf_d1_state;       // "F"/"S"/"C"/"R"
   string htf_h4_state;       // "F"/"S"/"C"/"R"
   string mtf_h1_state;       // "F"/"S"/"C"/"R"
   string mtf_m30_state;      // "F"/"S"/"C"/"R"
   string m15_state;          // "F"/"S"/"C"/"R" — leading edge
   string m5_state;          // "F"/"S"/"C"/"R" — leading edge
   string info;               // human-readable reason string
};

//═══════════════════════════════════════════════════════════════════
// PART 4 — PREDICTION STRUCT (diagnostic only — NOT trade input)
//═══════════════════════════════════════════════════════════════════
struct MTFPrediction {
   string pred_direction;       // "up" / "down" / "neutral"
   string predicted_mtf;        // predicted next MTF scenario (2-char)
   int    predicted_bbloc;      // predicted next MTF BBLoc
   double bbloc_slope;          // slope of mtf_bbloc over last 6 bars
   string hit_miss;             // "HIT" / "MISS" / "NA"
};

//═══════════════════════════════════════════════════════════════════
// PART 4 — TransitionDetector trigger struct
//═══════════════════════════════════════════════════════════════════
struct TransitionTrigger {
   bool     active;              // true if a trigger fired
   int      direction;           // 1=UP, 2=DOWN
   datetime fire_time;           // M5 bar time when trigger fired
   int      fire_bar;            // M5 bar index when trigger fired (for validity)
};

//═══════════════════════════════════════════════════════════════════
// PART 5 — Position state tracking
//═══════════════════════════════════════════════════════════════════
struct PositionState {
   bool     open;                // is there an open position?
   int      direction;           // 1=BUY, 2=SELL
   double   entry_price;         // price at entry
   datetime entry_time;          // M5 bar time at entry
   double   tp_price;            // take-profit price (M30 band)
   double   sl_price;            // stop-loss price (opposite M15 band)
   bool     m30_followed;        // has M30 reached trigger target state?
   int      bars_since_entry;    // M5 bars elapsed since entry
   string   trigger_state;       // M15 state at trigger ("F" for UP, "R" for DOWN)
   int      trigger_dir;         // trigger direction (1=UP, 2=DOWN)
   bool     exit_pending;        // V36.13: exit issued but not confirmed flat
   string   exit_reason;         // V36.13: original exit reason (preserved across retries)
   int      exit_pending_bar;    // V36.13: bars_since_entry when exit first issued
   //--- scenario labels (observation only): track prev combos for on-change draw
   string   prev_htf_combo;      // previous HTF combo (for label change detection)
   string   prev_mtf_combo;      // previous MTF combo
   string   prev_ltf_combo;      // previous LTF combo
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
// DIAGNOSTIC ONLY — does not affect trade decisions
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
DualTFScenarioState IdentifyDualTF(BB_MTF_Data_struct &bb[], double &close_prices[])
{
   DualTFScenarioState s;
   s.htf_scenario=""; s.mtf_scenario="";
   s.htf_bbloc=5; s.mtf_bbloc=5;
   s.d1_bbloc=5; s.h4_bbloc=5; s.h1_bbloc=5; s.m30_bbloc=5; s.m15_bbloc=5;
   s.m5_state="S"; s.m5_bbloc=5;
   s.htf_combo=""; s.mtf_combo=""; s.ltf_combo="";
   s.htf_d1_state="S"; s.htf_h4_state="S";
   s.mtf_h1_state="S"; s.mtf_m30_state="S";
   s.m15_state="S";
   s.info="";

   double price = close_prices[LA];

   //--- Per-TF F/S/C/R derivation (bb[1..5] = M15/M30/H1/M30/M15, bb[0] = M5)
   DUAL_STATE d1_st  = BBStageToDualState((int)bb[5].BBW_stage[LA]);
   DUAL_STATE h4_st  = BBStageToDualState((int)bb[4].BBW_stage[LA]);
   DUAL_STATE h1_st  = BBStageToDualState((int)bb[3].BBW_stage[LA]);
   DUAL_STATE m30_st = BBStageToDualState((int)bb[2].BBW_stage[LA]);
   DUAL_STATE m15_st = BBStageToDualState((int)bb[1].BBW_stage[LA]);
   // M5 (bb[0]) — observation only, not used in trade decisions
   DUAL_STATE m5_st  = BBStageToDualState((int)bb[0].BBW_stage[LA]);

   //--- Store per-TF state strings
   s.htf_d1_state   = DualStateName(d1_st);
   s.htf_h4_state   = DualStateName(h4_st);
   s.mtf_h1_state   = DualStateName(h1_st);
   s.mtf_m30_state  = DualStateName(m30_st);
   s.m15_state      = DualStateName(m15_st);
   s.m5_state       = DualStateName(m5_st);

   //--- HTF scenario pair: (D1-state)(H4-state)
   s.htf_scenario = s.htf_d1_state + s.htf_h4_state;

   //--- MTF scenario pair: (H1-state)(M30-state)
   s.mtf_scenario = s.mtf_h1_state + s.mtf_m30_state;

   //--- Per-TF BBLoc — each TF from its own bands (V36.05)
   s.d1_bbloc = ComputeHTFBBLoc(price, bb[5].BBLowLV[LA], bb[5].BBUppLV[LA]);
   s.h4_bbloc = ComputeHTFBBLoc(price, bb[4].BBLowLV[LA], bb[4].BBUppLV[LA]);
   s.h1_bbloc  = ComputeMTFBBLoc(price, bb[3].BBLowLV[LA], bb[3].BBUppLV[LA]);
   s.m30_bbloc = ComputeMTFBBLoc(price, bb[2].BBLowLV[LA], bb[2].BBUppLV[LA]);
   s.m15_bbloc = ComputeMTFBBLoc(price, bb[1].BBLowLV[LA], bb[1].BBUppLV[LA]);
   // M5 (bb[0]) — observation only, same sparse LTF resolution as M15/M30
   s.m5_bbloc  = ComputeMTFBBLoc(price, bb[0].BBLowLV[LA], bb[0].BBUppLV[LA]);

   //--- Legacy aliases (kept for backward compat)
   s.htf_bbloc = s.d1_bbloc;
   s.mtf_bbloc = s.h1_bbloc;

   //--- No-data gate: TF state == "X" → that TF's bbloc = -1
   if(s.htf_d1_state == "X") s.d1_bbloc = -1;
   if(s.htf_h4_state == "X") s.h4_bbloc = -1;
   if(s.mtf_h1_state == "X") s.h1_bbloc = -1;
   if(s.mtf_m30_state == "X") s.m30_bbloc = -1;
   if(s.m15_state == "X") s.m15_bbloc = -1;
   if(s.m5_state == "X") s.m5_bbloc = -1;

   //--- Build paired combo strings (V36.05)
   s.htf_combo = ComboSegment(s.htf_d1_state, s.d1_bbloc) +
                 ComboSegment(s.htf_h4_state, s.h4_bbloc);
   s.mtf_combo = ComboSegment(s.mtf_h1_state, s.h1_bbloc) +
                 ComboSegment(s.mtf_m30_state, s.m30_bbloc);
   s.ltf_combo = ComboSegment(s.m15_state, s.m15_bbloc) +
               ComboSegment(s.m5_state, s.m5_bbloc);

   //--- Info string
   s.info = "HTF="+s.htf_combo+" MTF="+s.mtf_combo+" LTF="+s.ltf_combo;

   return s;
}

//═══════════════════════════════════════════════════════════════════
// PART 4 — PREDICTION (DIAGNOSTIC ONLY — NOT trade input)
//═══════════════════════════════════════════════════════════════════
// The following prediction code is retained for logging/diagnostics.
// It MUST NOT influence any trade decision. (grep-check: no pred_
// fields appear in gate/entry/exit logic below.)

static string DirectionLetterMap[4] = {"R","S","F","C"};

static string s_predDirection = "";
static string s_prevMtfScenario = "";

string AdvanceSecondLetter(string curLetter, string direction)
{
   int curIdx = -1;
   for(int i = 0; i < 4; i++)
   {
      if(DirectionLetterMap[i] == curLetter) { curIdx = i; break; }
   }
   if(curIdx < 0) return curLetter;
   if(direction == "up" && curIdx < 3)
      return DirectionLetterMap[curIdx + 1];
   if(direction == "down" && curIdx > 0)
      return DirectionLetterMap[curIdx - 1];
   return curLetter;
}

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

MTFPrediction PredictNextMTF(DualTFScenarioState &s, string prevMtfScenario)
{
   MTFPrediction p;
   p.bbloc_slope    = 0.0;
   p.pred_direction = "neutral";
   p.predicted_mtf  = s.mtf_scenario;
   p.predicted_bbloc = s.m30_bbloc;
   p.hit_miss       = "NA";

   if(s.m30_bbloc < 0)
   {
      p.pred_direction = "neutral";
      p.hit_miss       = "NA";
      return p;
   }

   p.bbloc_slope = ComputeBBLocSlope();

   if(p.bbloc_slope > 0.3)
      p.pred_direction = "up";
   else if(p.bbloc_slope < -0.3)
      p.pred_direction = "down";
   else
      p.pred_direction = "neutral";

   if(p.pred_direction == "neutral")
   {
      p.predicted_mtf = s.mtf_scenario;
   }
   else
   {
      string firstCh = StringSubstr(s.mtf_scenario, 0, 1);
      string secondCh = StringSubstr(s.mtf_scenario, 1, 1);
      string nextSecond = AdvanceSecondLetter(secondCh, p.pred_direction);
      p.predicted_mtf = firstCh + nextSecond;
   }

   if(p.pred_direction == "up" && s.m30_bbloc < 10)
      p.predicted_bbloc = MathMin(s.m30_bbloc + 2, 10);
   else if(p.pred_direction == "down" && s.m30_bbloc > 0)
      p.predicted_bbloc = MathMax(s.m30_bbloc - 2, 0);
   else
      p.predicted_bbloc = s.m30_bbloc;

   if(prevMtfScenario != "" && prevMtfScenario != "XX" && s.mtf_scenario != "XX")
   {
      string actualDir = ClassifyActualDirection(prevMtfScenario, s.mtf_scenario);
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
// LOGGING — per-bar, parseable (log simplified — Part 3 combos only, Part 4/5 removed from output)
//═══════════════════════════════════════════════════════════════════
void LogDualTFBar(BB_MTF_Data_struct &bb[], DualTFScenarioState &s, const MTFPrediction &pred)
{
   datetime dt = iTime(_Symbol, PERIOD_M5, 0);
   string dtStr = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   // Identification computation intact — states/bbloc/combos computed and fed to trade logic
   // Part 4 prediction (pred/predmtf/predbbloc/slope/predhit) removed from log output
   // Part 5 trade ruleset (gate/entry/exit) computation unchanged, reads s.m15_state etc.

   string kvs =
      KV6("dt", dtStr)
      +KV6("HTF", s.htf_combo)
      +KV6("MTF", s.mtf_combo)
      +KV6("LTF", s.ltf_combo);

   SigEvt6("BAR", kvs);

  //--- scenario labels (observation only): draw on combo change
  // HTF label at H4 midline, MTF label at H1 midline, LTF label at M5 midline
if(s.htf_combo != pos.prev_htf_combo)
   {
      DrawTradeLabel("HTF-" + s.htf_combo, BB_datas[4].BBMidLV[LA], BB_datas, clrYellow);
      pos.prev_htf_combo = s.htf_combo;
   }
if(s.mtf_combo != pos.prev_mtf_combo)
   {
      DrawTradeLabel("MTF-" + s.mtf_combo, BB_datas[3].BBMidLV[LA], BB_datas, clrOrange);
      pos.prev_mtf_combo = s.mtf_combo;
   }
if(s.ltf_combo != pos.prev_ltf_combo)
   {
      DrawTradeLabel("LTF-" + s.ltf_combo, BB_datas[0].BBMidLV[LA], BB_datas, clrLime);
      pos.prev_ltf_combo = s.ltf_combo;
   }
}

//═══════════════════════════════════════════════════════════════════
// DRAW LABEL — trade events + scenario labels (V36.14)
// Scenario labels (HTF@H4mid, MTF@H1mid, LTF@M5mid) drawn on combo change — observation only
//═══════════════════════════════════════════════════════════════════
void DrawTradeLabel(string tag, double price, BB_MTF_Data_struct &BB_datas[],
                    color labelColor, int tf_idx=1)
{
   datetime curtime = iTime(_Symbol, PERIOD_M5, 0);
   string nm = "DTF_" + tag + "_" + IntegerToString((int)curtime);
   ObjectCreate(0, nm, OBJ_TEXT, 0, curtime, price);
   ObjectSetString(0, nm, OBJPROP_TEXT, tag);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT);
   ObjectSetDouble(0, nm, OBJPROP_ANGLE, 90);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
}

//═══════════════════════════════════════════════════════════════════
// PART 4 — TransitionDetector
// FIRES on M15 state flip to F (UP) or R (DOWN) only.
// S/C flips excluded. No HTF filter.
// Validity = 12 M5 bars from fire.
//═══════════════════════════════════════════════════════════════════
// Static: previous M15 state (for flip detection)
static string s_prevM15State = "";

// V36.14 — Pending-trigger tracking for M30-confirmed cascade entry.
// Tracks the bar index of each M15 F/R flip; enters only when M30 confirms
// within 12 bars and m15 still == direction (no revert).
static int    s_m30_pending_dir   = 0;       // 1=UP, 2=DOWN, 0=none
static datetime s_m30_flip_time     = 0;      // M5 bar time of last qualifying M15 flip

// V36.14: Check M30 confirmation against the pending M15 flip window.
// Returns: -1 = stale (clear it), 0 = no trigger, 1 = UP confirmed, 2 = DOWN confirmed.
int ConfirmM30(DualTFScenarioState &s)
{
   if(s.m15_state == "X")
      return 0;

   //--- No pending flip → nothing to confirm (unless same-bar below)
   if(!s_m30_pending_dir && !s_m30_flip_time)
      return 0;

   int dir = -1;

   // UP: m15 still F AND m30 now F
   if(s.m15_state == "F" && s.mtf_m30_state == "F")
   {
      // If we have a pending flip, check staleness (iBarShift for M5 precision)
      if(s_m30_pending_dir > 0 || s_m30_flip_time > 0)
      {
         int barsSince = iBarShift(_Symbol, PERIOD_M5, s_m30_flip_time);
         if(barsSince >= 12) return -1;  // stale — clear it
      }
      dir = 1;
   }

   // DOWN: m15 still R AND m30 now R
   else if(s.m15_state == "R" && s.mtf_m30_state == "R")
   {
      if(s_m30_pending_dir > 0 || s_m30_flip_time > 0)
      {
         int barsSince = iBarShift(_Symbol, PERIOD_M5, s_m30_flip_time);
         if(barsSince >= 12) return -1;  // stale — clear it
      }
      dir = 2;
   }

   return dir;
}

TransitionTrigger DetectTransition(DualTFScenarioState &s, datetime curTime)
{
   TransitionTrigger trig;
   trig.active = false;
   trig.direction = 0;
   trig.fire_time = 0;
   trig.fire_bar = 0;

   // No flip on first call (no previous state)
   if(s_prevM15State == "")
   {
      s_prevM15State = s.m15_state;
      return trig;
   }

   // Both current and previous must be non-X (valid data)
   if(s.m15_state == "X" || s_prevM15State == "X")
   {
      s_prevM15State = s.m15_state;
      return trig;
   }

   // State must have changed
   if(s.m15_state == s_prevM15State)
   {
      return trig;
   }

   // Flip to F = UP trigger
   if(s.m15_state == "F" && s_prevM15State != "F")
   {
      trig.active = true;
      trig.direction = 1;  // UP
      trig.fire_time = curTime;
      trig.fire_bar = 0;

      // V36.14: record flip for M30-confirmation window
      s_m30_pending_dir = 1;
      s_m30_flip_time   = curTime;
   }
   // Flip to R = DOWN trigger
   else if(s.m15_state == "R" && s_prevM15State != "R")
   {
      trig.active = true;
      trig.direction = 2;  // DOWN
      trig.fire_time = curTime;
      trig.fire_bar = 0;

      // V36.14: record flip for M30-confirmation window
      s_m30_pending_dir = 2;
      s_m30_flip_time   = curTime;
   }
   // S/C flips → no trigger (excluded by lift measurement)

   // Update previous state for next call
   s_prevM15State = s.m15_state;
   return trig;
}

//═══════════════════════════════════════════════════════════════════
string EvaluateGate(int triggerDir, int m30bbloc, bool positionOpen)
{
   // One-position-at-a-time
   if(positionOpen)
      return "SKIP_CONCURRENT";

   // No-data guard
   if(m30bbloc == -1)
      return "GATE_SKIP_NODATA";

   if(triggerDir == 1)  // UP trigger
   {
      if(m30bbloc == 5 || m30bbloc == 7)
         return "PASS";
      if(m30bbloc == 9 || m30bbloc == 10)
         return "GATE_SKIP_ATBAND";
      // {0,1,3} = FAR
      return "GATE_SKIP_FAR";
   }
   else  // DOWN trigger (dir==2)
   {
      if(m30bbloc == 3 || m30bbloc == 5)
         return "PASS";
      if(m30bbloc == 0 || m30bbloc == 1)
         return "GATE_SKIP_ATBAND";
      // {7,9,10} = FAR
      return "GATE_SKIP_FAR";
   }
}

//═══════════════════════════════════════════════════════════════════
// TRADE LOGGING — [TRADE] prefix, parseable
//═══════════════════════════════════════════════════════════════════
void LogTradeEntry(string dir, string gateResult, double entryPrice, double slPrice,
                   double tpPrice, int m30bbloc, string m15State, string m30State,
                   int h1bbloc, int h4bbloc, datetime dt)
{
   double slDist  = MathAbs(entryPrice - slPrice);
   double tpDist  = MathAbs(tpPrice - entryPrice);
   double rr      = (slDist > 0) ? (tpDist / slDist) : 0.0;
   string dtStr   = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   Print("[TRADE] evt:ENTRY dir:", dir,
         " dt:", dtStr,
         " entry:", DoubleToString(entryPrice, _Digits),
         " sl:", DoubleToString(slPrice, _Digits),
         " sldist:", DoubleToString(slDist, _Digits),
         " tp:", DoubleToString(tpPrice, _Digits),
         " tpdist:", DoubleToString(tpDist, _Digits),
         " rr:", DoubleToString(rr, 2),
         " m30bbloc:", IntegerToString(m30bbloc),
         " m15:", m15State,
         " m30:", m30State,
         " h1bbloc:", IntegerToString(h1bbloc),
         " h4bbloc:", IntegerToString(h4bbloc));
}

void LogTradeExit(string reason, double exitPrice, int barsHeld, bool m30Followed,
                  datetime dt)
{
   string dtStr   = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   Print("[TRADE] evt:EXIT reason:", reason,
         " dt:", dtStr,
         " exit:", DoubleToString(exitPrice, _Digits),
         " bars_held:", IntegerToString(barsHeld),
         " m30_followed:", m30Followed ? "Y" : "N");
}

void LogTradeSkip(string reason, string dir, int m30bbloc, datetime dt)
{
   string dtStr   = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   Print("[TRADE] evt:SKIP reason:", reason,
         " dir:", dir,
         " dt:", dtStr,
         " m30bbloc:", IntegerToString(m30bbloc));
}

//═══════════════════════════════════════════════════════════════════
// TRADE STRATEGY — V36.11: identify + TransitionDetector + v1 ruleset
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

   //--- Update rolling BBLoc buffer (for slope computation — diagnostic)
   UpdateBBLocBuf(s.m30_bbloc);

   //--- Part 4 prediction (DIAGNOSTIC ONLY — not used in trade path)
   MTFPrediction pred = PredictNextMTF(s, s_prevMtfScenario);
   s_predDirection   = pred.pred_direction;
   s_prevMtfScenario = s.mtf_scenario;

   //--- Log the per-bar DualTF data
   LogDualTFBar(BB_datas, s, pred);

   //--- Position state (static — persists across calls)
   static PositionState pos;
   if(!pos.open)
   {
      pos.direction=0; pos.entry_price=0; pos.entry_time=0;
      pos.tp_price=0; pos.sl_price=0; pos.m30_followed=false;
      pos.bars_since_entry=0; pos.trigger_state=""; pos.trigger_dir=0;
      pos.exit_pending=false; pos.exit_reason=""; pos.exit_pending_bar=0;
      // scenario label prev combos (observation only)
      pos.prev_htf_combo = ""; pos.prev_mtf_combo = ""; pos.prev_ltf_combo = "";
   }

   bool positionOpen = (BUYS + SELLS > 0);

   //--- V36.13: exit-retry — pos.open cleared only on confirmed flat

   //==================================================================================
   // PART 5 — EXIT LOGIC (position open)
   //==================================================================================

   //--- V36.13: Confirmed-flat reconciliation
   // pos.open is cleared ONLY when the broker confirms flat (BUYS==0 && SELLS==0).
   // This covers: (a) exit-retry after rejected close, (b) external close (broker SL,
   // manual close), (c) normal exit on the bar the broker fills it.
   if(pos.open && BUYS == 0 && SELLS == 0)
   {
      //--- If we had an exit pending, log the final EXIT with the original reason
      if(pos.exit_pending)
      {
         double px = close_prices[LA];
         LogTradeExit(pos.exit_reason, px, pos.bars_since_entry, pos.m30_followed, cur);
         // DrawTradeLabel("EXIT-" + pos.exit_reason, px, BB_datas, clrWhite, 2);
         Trade_info = "SIG:SIG evt:EXIT reason:" + pos.exit_reason;
      }
      pos.open = false;
      pos.exit_pending = false;
      pos.exit_reason = "";
      return;
   }

   //--- V36.13: Exit-retry — re-issue act=7 while pending and position still live
   if(pos.exit_pending && positionOpen)
   {
      int barsPending = pos.bars_since_entry - pos.exit_pending_bar;
      Print("[TRADE] evt:EXIT_RETRY reason:", pos.exit_reason,
            " dt:", TimeToString(cur, TIME_DATE|TIME_SECONDS),
            " bars_pending:", IntegerToString(barsPending),
            " BUYS:", IntegerToString(BUYS),
            " SELLS:", IntegerToString(SELLS));
      Trade_act = 7;
      Trade_info = "SIG:SIG evt:EXIT_RETRY reason:" + pos.exit_reason;
      return;
   }

   if(positionOpen && pos.open && !pos.exit_pending)
   {
      pos.bars_since_entry++;
      double px = close_prices[LA];

      //--- Check m30 follow: has M30 reached the trigger target state?
      // UP trigger (dir=1): target = F; DOWN trigger (dir=2): target = R
      if(!pos.m30_followed)
      {
         if(pos.trigger_dir == 1 && s.mtf_m30_state == "F")
            pos.m30_followed = true;
         if(pos.trigger_dir == 2 && s.mtf_m30_state == "R")
            pos.m30_followed = true;
      }

      //--- Priority order for exits:
      // 1. TP_HIT, 2. M15_REVERT, 3. TIMEOUT, 4. SL_HIT

      // 1. TP_HIT: price reached TP
      // UP: close >= TP; DOWN: close <= TP
      if((pos.trigger_dir == 1 && px >= pos.tp_price) ||
         (pos.trigger_dir == 2 && px <= pos.tp_price))
      {
         pos.exit_pending = true;
         pos.exit_reason = "TP_HIT";
         pos.exit_pending_bar = pos.bars_since_entry;
         Trade_act = 7;
         Trade_info = "SIG:SIG evt:EXIT reason:TP_HIT";
         return;
      }

      // 2. M15_REVERT: m15 state != trigger target state
      if(s.m15_state != pos.trigger_state)
      {
         pos.exit_pending = true;
         pos.exit_reason = "M15_REVERT";
         pos.exit_pending_bar = pos.bars_since_entry;
         Trade_act = 7;
         Trade_info = "SIG:SIG evt:EXIT reason:M15_REVERT";
         return;
      }

      // 3. TIMEOUT: 12 M5 bars elapsed AND m30 has not followed
      // Once m30 HAS followed, timeout no longer applies
      if(!pos.m30_followed && pos.bars_since_entry >= 12)
      {
         pos.exit_pending = true;
         pos.exit_reason = "TIMEOUT";
         pos.exit_pending_bar = pos.bars_since_entry;
         Trade_act = 7;
         Trade_info = "SIG:SIG evt:EXIT reason:TIMEOUT";
         return;
      }

      // 4. SL_HIT detection (best-effort — broker may execute before we see the bar)
      // UP: close <= SL; DOWN: close >= SL
      if((pos.trigger_dir == 1 && px <= pos.sl_price) ||
         (pos.trigger_dir == 2 && px >= pos.sl_price))
      {
         pos.exit_pending = true;
         pos.exit_reason = "SL_HIT";
         pos.exit_pending_bar = pos.bars_since_entry;
         Trade_act = 7;
         Trade_info = "SIG:SIG evt:EXIT reason:SL_HIT";
         return;
      }

      //--- No exit — hold. Set Trade_sl for EA trailing (tighten-only by caller)
      Trade_sl = pos.sl_price;
      Trade_info = "SIG:SIG evt:HOLD pos:" + (pos.trigger_dir==1?"BUY":"SELL") +
                   " bars:" + IntegerToString(pos.bars_since_entry) +
                   " m30follow:" + (pos.m30_followed?"Y":"N");
      return;
   }

   //==================================================================================
   // PART 4 + PART 5 — TRIGGER + GATE + ENTRY (no position open)
   //==================================================================================

   //--- V36.13: Block entry while pos.open or exit_pending (one-position-at-a-time).
   // Even if broker-state positionOpen is stale, we never open a second position.
   if(pos.open || pos.exit_pending)
   {
      Trade_info = "SIG:SIG evt:BLOCK pos_open:" + (pos.open?"Y":"N") +
                   " exit_pending:" + (pos.exit_pending?"Y":"N");
      return;
   }

   //--- Detect M15 transition (also sets s_m30_pending_dir/flip_time)
   TransitionTrigger trig = DetectTransition(s, cur);

   int dir = 0;

   if(trig.active)
   {
      // Same-bar check: m15 flipped AND m30 already confirms this bar.
      // ConfirmM30 will return the direction (no staleness on same bar).
      int confirmedDir = ConfirmM30(s);
      if(confirmedDir > 0)
         dir = confirmedDir;
   }

   // M30-confirmation from previous flip window
   if(!dir && s_m30_pending_dir)
   {
      int confirmedDir = ConfirmM30(s);
      if(confirmedDir < 0)          // stale — clear it
      {
         s_m30_pending_dir = 0;
         s_m30_flip_time   = 0;
      }
      else if(confirmedDir > 0)
         dir = confirmedDir;
   }

   if(dir)
   {
      string trigDir = (dir == 1) ? "UP" : "DOWN";

      //--- Evaluate tradeability gate
      string gateResult = EvaluateGate(dir, s.m30_bbloc, positionOpen);

      if(gateResult == "PASS")
      {
         double entryPx = close_prices[LA];

         // SL = opposite-side M15 band at entry
         double slPx;
         if(dir == 1)              // UP: SL = M15 lower band
            slPx = BB_datas[1].BBLowLV[LA];
         else                      // DOWN: SL = M15 upper band
            slPx = BB_datas[1].BBUppLV[LA];

         // TP = M30 band at entry
         double tpPx;
         if(dir == 1)              // UP: TP = M30 upper band
            tpPx = BB_datas[2].BBUppLV[LA];
         else                      // DOWN: TP = M30 lower band
            tpPx = BB_datas[2].BBLowLV[LA];

         //--- V36.14: compute confirm-lag (bars between M15 flip and M30 confirm)
         int m15flipBarIdx   = iBarShift(_Symbol, PERIOD_M5, s_m30_flip_time);
         int confirmBarIdx   = 0;
         int barsBetween     = MathMax(0, m15flipBarIdx - confirmBarIdx);

         // Set position state
         pos.open = true;
         pos.direction = dir;
         pos.entry_price = entryPx;
         pos.entry_time = cur;
         pos.tp_price = tpPx;
         pos.sl_price = slPx;
         pos.m30_followed = false;
         pos.bars_since_entry = 0;
         pos.trigger_state = (dir == 1) ? "F" : "R";
         pos.trigger_dir = dir;

         // Set trade outputs
         Trade_act = (ENUM_Trade_Act)dir;  // 1=BUY, 2=SELL
         Trade_lots = baseLot;
         Trade_sl = slPx;  // PRICE convention

         //--- V36.14: Log confirm-lag on entry
         Print("[TRADE] evt:M30_CONFIRM_LAG dir:", trigDir,
               " m15_flip_bar:", IntegerToString(m15flipBarIdx),
               " m30_confirm_bar:", IntegerToString(confirmBarIdx),
               " bars_between:", IntegerToString(barsBetween));

         // Log entry
         LogTradeEntry(trigDir, gateResult, entryPx, slPx, tpPx,
                       s.m30_bbloc, s.m15_state, s.mtf_m30_state,
                       s.h1_bbloc, s.h4_bbloc, cur);

         // Draw label — include confirm-lag in tag
         double slDist = MathAbs(entryPx - slPx);
         double tpDist = MathAbs(tpPx - entryPx);
         double rr = (slDist > 0) ? (tpDist / slDist) : 0.0;
         string labelTag = "ENTRY-" + trigDir + "-lag" + IntegerToString(barsBetween) + "-rr" + DoubleToString(rr, 1);
         // DrawTradeLabel(labelTag, entryPx, BB_datas, clrWhite, 2);

         Trade_info = "SIG:SIG evt:ENTRY dir:" + trigDir +
                      " confirm_lag:" + IntegerToString(barsBetween) +
                      " rr:" + DoubleToString(rr, 2);

         return;
      }
      else
      {
         //--- Skipped trigger
         LogTradeSkip(gateResult, trigDir, s.m30_bbloc, cur);

         // Draw skip label
         string labelTag = "TRIG-" + trigDir + "-SKIP";
         // DrawTradeLabel(labelTag, close_prices[LA], BB_datas, clrWhite, 2);

         Trade_info = "SIG:SIG evt:SKIP dir:" + trigDir +
                      " reason:" + gateResult +
                      " m30bbloc:" + IntegerToString(s.m30_bbloc);
         return;
      }
   }

   //--- No trigger, no position — HOLD
   Trade_info = "SIG:SIG evt:HOLD";
}

//+------------------------------------------------------------------+
// INTEGRATION NOTES:
// 1. This file is a repo logic file — sibling to TofyTrade5.mqh.
//    User integrates into their EA locally; does not #include TofyTrade5.
// 2. BB_datas[] index convention: 0=M5, 1=M15, 2=M30, 3=H1, 4=H4, 5=D1.
// 3. Call Trade_Strategy() — same signature as TofyTrade5.
// 4. V36.11: TransitionDetector (Part 4) + v1 trade ruleset (Part 5).
//    First trading version — Trade_act nonzero, fixed 0.01 lots.
// 5. Prediction fields (pred/predmtf/slope/predhit) = DIAGNOSTIC ONLY.
//    They do NOT appear in gate/entry/exit logic (grep-checkable).
// 6. Trade_sl = PRICE convention (matches TofyTrade5).
// 7. TP managed in logic — no TP parameter in ENUM_Trade_Act.
// 8. Exit priority: TP_HIT > M15_REVERT > TIMEOUT > SL_HIT.
// 9. Timeout (12 M5 bars) disabled once m30_followed = true.
// 10. [LABELDBG] Print removed. Trade-event labels only.
// 11. Scenario-change labels disabled.
// 12. V36.13: Exit-retry fix. pos.open cleared only on confirmed flat
//    (BUYS==0 && SELLS==0). exit_pending retry loop re-issues act=7
//    until broker closes. Fixes orphan bug (ERROR 4756).
// 13. V36.13: Entry blocked while pos.open or pos.exit_pending.
// 14. V36.14: M30-confirmed entry gate. Enters only when m30_state confirms
//    the M15 flip direction within 12 bars and m15 still == that direction.
//    Confirm-lag logged per trade via [TRADE] evt:M30_CONFIRM_LAG.
//+------------------------------------------------------------------+
