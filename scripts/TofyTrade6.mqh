#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "36.01"
//+------------------------------------------------------------------+
//| TofyTrade6 — DualTF Stack logic                                   |
//| Part 3 (IDENTIFY) + REAL BBLoc + LOGGING.                         |
//| Part 4 prediction is a minimal experimental stub                  |
//| (coarse-data prediction scored 1.2% transition accuracy,          |
//|  commit 0229a8b — Part 4/5 to be redesigned after viewing         |
//|  real BBLoc data on charts).                                      |
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
enum DUAL_STATE { DS_F=0, DS_S=1, DS_C=2, DS_R=3 };   // Fly-up, Shrink, Compress, Fly-down

string DualStateName(DUAL_STATE d) {
   switch(d){
      case DS_F: return "F";
      case DS_S: return "S";
      case DS_C: return "C";
      case DS_R: return "R";
      default:   return "?";
   }
}

//═══════════════════════════════════════════════════════════════════
// STRUCT — DualTFScenarioState  (design doc §3.1)
//═══════════════════════════════════════════════════════════════════
struct DualTFScenarioState {
   string htf_scenario;       // 2-char: (D1-state)(H4-state), e.g. "FS"
   string mtf_scenario;       // 2-char: (H1-state)(M30-state), e.g. "FC"
   int    htf_bbloc;          // 0-10, real price-vs-D1/H4-band
   int    mtf_bbloc;          // {0,1,3,5,7,9,10}, real price-vs-H1/M30-band
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
   if(width <= 0.0) return 5.0;   // degenerate: bands collapsed -> mid
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
   return SnapToMTFScale(raw);
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

   //--- Real BBLoc — HTF (use D1 bands for full resolution)
   s.htf_bbloc = ComputeHTFBBLoc(price, bb[5].BBLowLV[LA], bb[5].BBUppLV[LA]);

   //--- Real BBLoc — MTF (use H1 bands, snap to sparse scale)
   s.mtf_bbloc = ComputeMTFBBLoc(price, bb[3].BBLowLV[LA], bb[3].BBUppLV[LA]);

   //--- Info string
   s.info = "HTF="+s.htf_scenario+"(D1="+s.htf_d1_state+",H4="+s.htf_h4_state+") " +
            "MTF="+s.mtf_scenario+"(H1="+s.mtf_h1_state+",M30="+s.mtf_m30_state+") " +
            "M15="+s.m15_state+" HTF-BBLoc="+IntegerToString(s.htf_bbloc) +
            " MTF-BBLoc="+IntegerToString(s.mtf_bbloc);

   return s;
}

//═══════════════════════════════════════════════════════════════════
// LOGGING — per-bar, parseable (the redesign dataset)
//═══════════════════════════════════════════════════════════════════
// Log format (colon-separated, no spaces in values):
// [DUALTF] SIG:DUALTF evt:BAR dt:<datetime>
//   d1:stg:<BBW_stage> mid:<diffMid> ud:<BBUpDn> state:<F/S/C/R>
//   h4:stg:<...> mid:<...> ud:<...> state:<...>
//   h1:stg:<...> mid:<...> ud:<...> state:<...>
//   m30:stg:<...> mid:<...> ud:<...> state:<...>
//   m15:stg:<...> mid:<...> ud:<...> state:<...>
//   htf:<scenario> htfbbloc:<bbloc>
//   mtf:<scenario> mtfbbloc:<bbloc>

void LogDualTFBar(BB_MTF_Data_struct &bb[], DualTFScenarioState &s)
{
   datetime dt = iTime(_Symbol, PERIOD_M5, 0);
   string dtStr = TimeToString(dt, TIME_DATE|TIME_SECONDS);

   string kvs =
      KV6("dt", dtStr)
      +KV6("d1:stg", IntegerToString((int)bb[5].BBW_stage[LA]))
      +KV6("d1:mid", IntegerToString(bb[5].BB_diffMid_Trend[LA]))
      +KV6("d1:ud",  IntegerToString(bb[5].BBUpDn_state[LA]))
      +KV6("d1:state", s.htf_d1_state)
      +KV6("h4:stg", IntegerToString((int)bb[4].BBW_stage[LA]))
      +KV6("h4:mid", IntegerToString(bb[4].BB_diffMid_Trend[LA]))
      +KV6("h4:ud",  IntegerToString(bb[4].BBUpDn_state[LA]))
      +KV6("h4:state", s.htf_h4_state)
      +KV6("h1:stg", IntegerToString((int)bb[3].BBW_stage[LA]))
      +KV6("h1:mid", IntegerToString(bb[3].BB_diffMid_Trend[LA]))
      +KV6("h1:ud",  IntegerToString(bb[3].BBUpDn_state[LA]))
      +KV6("h1:state", s.mtf_h1_state)
      +KV6("m30:stg", IntegerToString((int)bb[2].BBW_stage[LA]))
      +KV6("m30:mid", IntegerToString(bb[2].BB_diffMid_Trend[LA]))
      +KV6("m30:ud",  IntegerToString(bb[2].BBUpDn_state[LA]))
      +KV6("m30:state", s.mtf_m30_state)
      +KV6("m15:stg", IntegerToString((int)bb[1].BBW_stage[LA]))
      +KV6("m15:mid", IntegerToString(bb[1].BB_diffMid_Trend[LA]))
      +KV6("m15:ud",  IntegerToString(bb[1].BBUpDn_state[LA]))
      +KV6("m15:state", s.m15_state)
      +KV6("htf", s.htf_scenario)
      +KVi6("htfbbloc", s.htf_bbloc)
      +KV6("mtf", s.mtf_scenario)
      +KVi6("mtfbbloc", s.mtf_bbloc);

   SigEvt6("BAR", kvs);
}

//═══════════════════════════════════════════════════════════════════
// DRAW LABEL — ported from TofyTrade5
// DEPENDENCY: DRAW_LABEL macro provided by EA includes (TofyIncludeSimple.mqh)
//═══════════════════════════════════════════════════════════════════
void DrawGateLabel(string tag, double price, BB_MTF_Data_struct &BB_datas[],
                   color labelColor, int tf_idx=1)
{
   datetime curtime = iTime(_Symbol, PERIOD_M5, 0);
   DRAW_LABEL(tag, curtime, price, labelColor,
              BB_datas[tf_idx].BBFontSize, BB_datas[tf_idx].BBArrowWidth,
              90, ANCHOR_UPPER, BB_datas[tf_idx]);
}

//═══════════════════════════════════════════════════════════════════
// TRADE STRATEGY — V36.01: identify + BBLoc + log + draw only
// NO trades — prediction unvalidated (1.2%), Part 5 deferred.
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

   //--- Log the per-bar DualTF data (produces the redesign dataset)
   LogDualTFBar(BB_datas, s);

   //--- Draw chart label: scenario + BBLoc visible on backtest chart
   string tag = "HTF:"+s.htf_scenario+"["+IntegerToString(s.htf_bbloc)+
                "] MTF:"+s.mtf_scenario+"["+IntegerToString(s.mtf_bbloc)+"]";
   DrawGateLabel(tag, close_prices[LA], BB_datas, clrWhite, 1);

   //--- Set Trade_info to the scenario summary
   Trade_info = s.info;

   // V36.01: identify + BBLoc + log + draw only. NO trades — prediction
   // unvalidated (1.2%), Part 5 deferred.
}

//═══════════════════════════════════════════════════════════════════
// PART 4 — MINIMAL EXPERIMENTAL STUB
//
// STUB — coarse-data prediction scored 1.2% transition accuracy.
// Part 4 to be redesigned after viewing real BBLoc data.
// NOT for trade decisions.
//═══════════════════════════════════════════════════════════════════
struct MTFPrediction_EXPERIMENTAL {
   string next_mtf_scenario;   // predicted next MTF (2-char)
   int    next_mtf_bbloc;      // predicted MTF BBLoc
   int    confidence;          // 0-100
   bool   is_transition;       // MTF scenario changes
   string reason;
};

//--- State machine helper: char 'F'/'S'/'C'/'R' -> DUAL_STATE
DUAL_STATE CharToDualState(string ch)
{
   if(ch=="F") return DS_F;
   if(ch=="S") return DS_S;
   if(ch=="C") return DS_C;
   if(ch=="R") return DS_R;
   return DS_S;
}

//--- Valid next states per the state machine (design doc §4):
// F -> {S, persist}, S -> {F, C, persist}, C -> {F, R, persist}, R -> {S, persist}
void ValidNextStates(DUAL_STATE cur, string &next1, string &next2, string &next3)
{
   next3 = "persist";  // always valid
   switch(cur) {
      case DS_F: next1="S"; next2=""; break;
      case DS_S: next1="F"; next2="C"; break;
      case DS_C: next1="F"; next2="R"; break;
      case DS_R: next1="S"; next2=""; break;
      default:   next1="S"; next2=""; break;
   }
}

MTFPrediction_EXPERIMENTAL PredictNextMTF_EXPERIMENTAL(DualTFScenarioState &s)
{
   MTFPrediction_EXPERIMENTAL p;
   p.next_mtf_scenario = s.mtf_scenario;   // persist (safe default)
   p.next_mtf_bbloc    = s.mtf_bbloc;
   p.confidence        = 0;                 // zero — not for decisions
   p.is_transition     = false;
   p.reason = "STUB — persist default. Coarse-data prediction scored 1.2% transition accuracy. " +
              "Part 4 to be redesigned after viewing real BBLoc data. NOT for trade decisions.";

   //--- Minimal: return valid-next-states per the state machine
   // (no full prediction rules — they'll be redesigned on real data)
   DUAL_STATE h1Cur  = CharToDualState(StringSubstr(s.mtf_scenario,0,1));
   DUAL_STATE m30Cur = CharToDualState(StringSubstr(s.mtf_scenario,1,1));
   string h1n1,h1n2,h1n3, m30n1,m30n2,m30n3;
   ValidNextStates(h1Cur, h1n1, h1n2, h1n3);
   ValidNextStates(m30Cur, m30n1, m30n2, m30n3);

   p.reason += " H1-valid-next:" + h1n1;
   if(h1n2 != "") p.reason += "," + h1n2;
   p.reason += " M30-valid-next:" + m30n1;
   if(m30n2 != "") p.reason += "," + m30n2;

   return p;
}

//═══════════════════════════════════════════════════════════════════
// PART 5 — DEFERRED
//
// Trade action deferred until Part 4 redesigned on real data.
// No implementation — the prediction engine (Part 4) scored 1.2%
// on coarse data and must be redesigned using real BBLoc data
// generated by this file's logging before trade logic is written.
//═══════════════════════════════════════════════════════════════════
// TradeAction struct and DecideDualTFAction function — DEFERRED.
// See header comment: "Part 5 deferred stub."
//+------------------------------------------------------------------+
// INTEGRATION NOTES:
// 1. This file is a repo logic file — sibling to TofyTrade5.mqh.
//    User integrates into their EA locally; does not #include TofyTrade5.
// 2. BB_datas[] index convention: 0=M5, 1=M15, 2=M30, 3=H1, 4=H4, 5=D1.
// 3. Call Trade_Strategy() — same signature as TofyTrade5. It calls
//    IdentifyDualTF + LogDualTFBar + DrawGateLabel internally.
// 4. Trade_Strategy returns Trade_act=0 (HOLD) — no trades. This is a
//    visualization/data pass. PredictNextMTF_EXPERIMENTAL is a STUB.
// 5. Part 5 (trade action) is DEFERRED — no DecideDualTFAction yet.
// 6. The real BBLoc (ComputeHTFBBLoc / ComputeMTFBBLoc) is the KEY
//    feature — it produces data the analysis side cannot generate.
// 7. DrawGateLabel depends on DRAW_LABEL macro from EA includes.
//+------------------------------------------------------------------+
