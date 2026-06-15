#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "31.01"
//+------------------------------------------------------------------+
//| TofyTrade5 — three-layer architecture, 1:1 with                  |
//| references/backtest_chart_analysis.md                            |
//|   Layer 1 IdentifyScenario = Part 3 (+ §12 CHECK-HTF, §12d,      |
//|                              §13 phases, Part 6 Step 2b)         |
//|   Layer 2 PredictNext      = Part 4 (Rules 1-5)                  |
//|   Layer 3 DecideAction     = Part 5 (E1-E6/X1-X4, firing matrix) |
//| RULES:                                                           |
//|   - every branch cites its doc section. Uncited logic forbidden. |
//|   - gates abolished: 3 invariants + firing matrix + assertions   |
//|   - log grammar: [TRADEINFO] SIG:SIG evt:<EVT> key:value ...     |
//|     values never contain ':' or spaces                           |
//+------------------------------------------------------------------+
#define MIN_HOLD_BARS          3     // minimum M5 bars between entries (kept from v30)
#define POST_EXIT_COOLDOWN     5     // M5 bars blocking re-entry after act=7
#define MAX_FLOATING_LOSS_USD  50.0  // INVARIANT 1 — checked first, ungateable
#define MAGIC_NUMBER           898989 // EA magic number (verified in tester.ini)
#define LOG_VERBOSE            false // second-line driver diagnostics (display only)

#include <TofyIncludeSimple.mqh>

//═══════════════════════════════════════════════════════════════════
// ADAPTER SECTION — wire these to the REAL fields in
// TofyIncludeSimple.mqh before first compile. Everything below this
// section uses only verified fields (BBW_stage, BB_diffMid_Trend,
// BB_Mid, BB_diffMid, ATRSL1BUF.*) plus these adapters.
//═══════════════════════════════════════════════════════════════════

// --- diffBBW (band width velocity, doc §4b; log formula: (WLV[n]-WLV[n+1])*100) ---
// CRITICAL: log uses ABSOLUTE formula (w_now - w_prev)*100, NOT percentage.
// Verified against V30.02 log: WLV cur=4.66, prev=5.46 → log value -79.94
//   Absolute:  (4.66-5.46)*100 = -80.0 ≈ -79.94 ✓
//   Percentage: (4.66-5.46)/5.46*100 = -14.65 ✗
// The previous percentage formula was wrong — every threshold was mis-scaled.
double ADiffBBW(BB_MTF_Data_struct &bb[], int tf, int sh=0)
{
   double w_now  = ABBUpper(bb,tf,sh)   - ABBLower(bb,tf,sh);
   double w_prev = ABBUpper(bb,tf,sh+1) - ABBLower(bb,tf,sh+1);
   return (w_now - w_prev)*100.0;                      // §4b: absolute ×100 (matches log)
}

// --- band levels (doc PriceLoc needs BBUppLV/BBLowLV) -------------
// TODO(ClaudeCode): wire to the real upper/lower band arrays
// (check names like BB_Upper/BB_Lower/BBUppLV/BBLowLV).
double ABBUpper(BB_MTF_Data_struct &bb[], int tf, int sh=0)
{  return bb[tf].BBUppLV[sh]; }      // ← VERIFY field name
double ABBLower(BB_MTF_Data_struct &bb[], int tf, int sh=0)
{  return bb[tf].BBLowLV[sh]; }      // ← VERIFY field name

// --- floating P/L of our positions (INVARIANT 1) ------------------
// Magic-number filter required: EA uses MAGIC_NUMBER=898989 (tester.ini)
// Without this filter, P/L from other EAs/manual trades on the same symbol
// corrupts the EMERGENCY invariant, causing false triggers or missed exits.
double AFloatingPL()
{
   double pl=0.0;
   for(int i=OrdersTotal()-1; i>=0; i--) {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol()!=_Symbol) continue;
      if(OrderMagicNumber()!=MAGIC_NUMBER) continue;     // filter to EA's own trades
      pl += OrderProfit()+OrderSwap()+OrderCommission();
   }
   return pl;
}

//═══════════════════════════════════════════════════════════════════
// SIG LOGGING — agreed grammar:
//   2026.01.02 18:45:02 [TRADEINFO] SIG:SIG evt:DECISION sc:B2 ...
// disciplines: ':' only as separator (split on FIRST ':'), no spaces
// or ':' inside values, multiword values use '-'.
//═══════════════════════════════════════════════════════════════════
string KV(string k, string v)            { return " "+k+":"+v; }
string KVi(string k, int v)              { return " "+k+":"+IntegerToString(v); }
string KVd(string k, double v, int dp=2) { return " "+k+":"+DoubleToString(v,dp); }

void SigEvt(string evt, string kvs)
{  Print("[TRADEINFO] SIG:SIG", KV("evt",evt), kvs); }

//═══════════════════════════════════════════════════════════════════
// ENUMS & STATE STRUCTS
//═══════════════════════════════════════════════════════════════════
enum SCENARIO { SC_NONE=0,
   SC_A1, SC_A2, SC_A3,                       // Tier 1            // Part 3
   SC_B1, SC_B2, SC_B3,                       // Tier 2 shallow
   SC_E1, SC_E2, SC_E3L, SC_E4,               // Tier 2 deep (E3L=loading)
   SC_G1, SC_G2, SC_G3, SC_G4,                // Tier 2 direction pivot
   SC_D1s, SC_D2s, SC_D3s,                    // Tier 3 rest
   SC_F1, SC_F2, SC_F3,                       // Tier 3 release
   SC_C1, SC_C2, SC_C3 };                     // Tier 3 reversal

enum PHASE { PH_NONE=0, PH_1, PH_2, PH_3A, PH_3B_INTO, PH_3B_OUT, PH_4, PH_5, PH_6 };

string ScenarioName(SCENARIO s) {
   switch(s){ case SC_A1:return"A1";case SC_A2:return"A2";case SC_A3:return"A3";
   case SC_B1:return"B1";case SC_B2:return"B2";case SC_B3:return"B3";
   case SC_E1:return"E1";case SC_E2:return"E2";case SC_E3L:return"E3";case SC_E4:return"E4";
   case SC_G1:return"G1";case SC_G2:return"G2";case SC_G3:return"G3";case SC_G4:return"G4";
   case SC_D1s:return"D1";case SC_D2s:return"D2";case SC_D3s:return"D3";
   case SC_F1:return"F1";case SC_F2:return"F2";case SC_F3:return"F3";
   case SC_C1:return"C1";case SC_C2:return"C2";case SC_C3:return"C3";
   default:return"NA";} }
string PhaseName(PHASE p) {
   switch(p){ case PH_1:return"1";case PH_2:return"2";case PH_3A:return"3A";
   case PH_3B_INTO:return"3BI";case PH_3B_OUT:return"3BO";case PH_4:return"4";
   case PH_5:return"5";case PH_6:return"6";default:return"NA";} }
string TFName(int i){ switch(i){case 0:return"M5";case 1:return"M15";case 2:return"M30";
   case 3:return"H1";case 4:return"H4";case 5:return"D1";case 6:return"W1";default:return"NA";} }

struct ScenarioState {
   SCENARIO scenario;
   PHASE    phase;
   int      cas_shrinkTF;       // §12d: highest TF in shrink (1=M15..5=D1, -1 none)
   int      cas_sqzCount;       // §12d: count of M5..H1 TFs in SQZ
   bool     b1_block;           // Part 5 B1: M15 diffMid >= 3
   bool     b2_pink;            // Part 5 B2: M15 AND M30 both BBW 400-499
   // ── Part 6 Step 2b container (W1 addendum) ──
   int      container_tf;       // highest TF in committed fly, -1 if none
   int      container_dir;      // its diffMid (1/2), 0 if none
   double   container_diffbbw;  // health: >0 room, <=0 aging
   int      priceloc;           // vs container: -2 below_lower -1 at_lower 0 inside +1 at_upper +2 above_upper
   int      pivot_substate;     // G-tier display: 0=N/A 1=PIVOT-PENDING(m5 not broken) 2=G-REVERSAL(m5 broken)
   string   info;
};

struct Prediction {
   int      direction;          // Part 4 Rule 1: 1 BUY / 2 SELL / 0 NEUTRAL
   int      target_tf;          // Part 4 Rule 2: container_tf (fallback per scenario)
   int      timeline_bars;      // Part 4 Rule 3 (coarse)
   SCENARIO next_scenario;      // Part 4 Rule 4
   int      confidence;         // Part 4 Rule 5: 0-100
   bool     reversal;
   string   info;
};

struct TradeAction {
   int      act;                // ENUM_Trade_Act: 0 hold / 1 exit_sell+buy / 2 exit_buy+sell / 7 exit_all
   string   condition_id;       // E1..E6 / X1..X4 / VETO / WAIT
   double   size_mult;          // EDIT V5: min(matrix ceiling, confidence size, decoder size)
   double   stop_price;
   string   info;
};

//═══════════════════════════════════════════════════════════════════
// KEPT HELPERS (ported unchanged or near-unchanged from TofyTrade4)
//═══════════════════════════════════════════════════════════════════
double CalcLotSize(int tfAgreeCount, double baseLot) {           // kept
   if(tfAgreeCount>=3) return baseLot;
   if(tfAgreeCount==2) return baseLot*0.75;
   if(tfAgreeCount==1) return baseLot*0.5;
   return 0.0;
}
int CountTFAgreement(BB_MTF_Data_struct &BB_datas[], int direction, int maxTF) {  // kept
   int count=0;
   for(int i=0; i<=maxTF; i++) {
      int stage=BB_datas[i].BBW_stage[LA];
      int trend=BB_datas[i].BB_diffMid_Trend[LA];
      if(direction==1 && (stage==511||stage==512) && (trend==1||trend==5)) count++;
      if(direction==2 && (stage==521||stage==522) && (trend==2||trend==4)) count++;
   }
   return count;
}
double GetATRSLStop(ATRSLBUF_struct &ATRSL1BUF, int direction) {  // kept verbatim
   if(direction==1)
      return (ATRSL1BUF.dir==0) ? ATRSL1BUF.ATRSLLower[LA] : ATRSL1BUF.ATRSLMid[LA];
   if(direction==2)
      return (ATRSL1BUF.dir==1) ? ATRSL1BUF.ATRSLUpper[LA] : ATRSL1BUF.ATRSLMid[LA];
   return 0.0;
}
#define GATE_CLR_EXIT  clrCrimson
#define GATE_CLR_BUY   clrLime
#define GATE_CLR_SELL  clrOrangeRed
#define GATE_CLR_WAIT  clrYellow
#define GATE_CLR_PINK  clrMagenta
#define GATE_CLR_LOAD  clrGold
#define GATE_CLR_NOISE clrDimGray
#define GATE_CLR_AQUA  clrAqua

//── Tier colors for scenario labels (display only) ───────────────────
#define TIER_CLR_A        clrDarkGray
#define TIER_CLR_B        clrYellow
#define TIER_CLR_E        clrDarkOrange
#define TIER_CLR_G        clrRed            // provisional — OOS-UNVALIDATED
#define TIER_CLR_F        clrLimeGreen
#define TIER_CLR_C        clrMagenta
#define TIER_CLR_PIVOT    clrWhite

void DrawGateLabel(string tag, double price, BB_MTF_Data_struct &BB_datas[],
                   color labelColor, int tf_idx=1)               // kept verbatim
{
   datetime curtime = iTime(_Symbol, PERIOD_M5, 0);
   DRAW_LABEL(tag, curtime, price, labelColor,
              BB_datas[tf_idx].BBFontSize, BB_datas[tf_idx].BBArrowWidth,
              90, ANCHOR_UPPER, BB_datas[tf_idx]);
}
int DynMinHold(int trigTF) {                                     // kept
   if(trigTF >= 3) return 18;
   if(trigTF == 2) return 12;
   if(trigTF == 1) return 6;
   return MIN_HOLD_BARS;
}

bool IsSQZ(int stg)    { return (stg>=400 && stg<500); }
bool IsFlyUp(int stg)  { return (stg==511||stg==512); }
bool IsFlyDn(int stg)  { return (stg==521||stg==522); }
bool IsFly(int stg)    { return IsFlyUp(stg)||IsFlyDn(stg); }
bool IsShrink(int stg) { return (stg==513||stg==523); }

//── Scenario label helpers (display only — read IdentifyScenario output) ──
color ScenarioLabelColor(SCENARIO sc) {
   switch(sc){
      case SC_A1:case SC_A2:case SC_A3: return TIER_CLR_A;
      case SC_B1:case SC_B2:case SC_B3: return TIER_CLR_B;
      case SC_E1:case SC_E2:case SC_E3L:case SC_E4: return TIER_CLR_E;
      case SC_G1:case SC_G2:case SC_G3:case SC_G4: return TIER_CLR_G;
      case SC_F1:case SC_F2:case SC_F3: return TIER_CLR_F;
      case SC_C1:case SC_C2:case SC_C3: return TIER_CLR_C;
      case SC_D1s:case SC_D2s:case SC_D3s: return TIER_CLR_B;
      default: return clrWhite; } }

//═══════════════════════════════════════════════════════════════════
// LAYER 1 — IdentifyScenario                       (doc Part 3 etc.)
//═══════════════════════════════════════════════════════════════════
// diffBBW_H4 ring buffer for phase classification (§13)
#define PH_LOOKBACK 12
double  g_dbbw_ring[PH_LOOKBACK];
int     g_dbbw_n = 0;

// Decision 5/6: prior-bar H1-SQZ state (persisted across calls)
static bool s_prevH1Sqz = false;

// Early F-tier: 2 recent diffBBW_H4 values (current + prev)
static double s_dbbwH4_hist[2];
static int    s_dbbwH4_hist_n = 0;

void RingPush(double v) {
   for(int i=PH_LOOKBACK-1;i>0;i--) g_dbbw_ring[i]=g_dbbw_ring[i-1];
   g_dbbw_ring[0]=v;
   if(g_dbbw_n<PH_LOOKBACK) g_dbbw_n++;
}

void DbbwH4HistPush(double v) {
   s_dbbwH4_hist[1] = s_dbbwH4_hist[0];
   s_dbbwH4_hist[0] = v;
   if(s_dbbwH4_hist_n < 2) s_dbbwH4_hist_n++;
}

PHASE ClassifyPhase(BB_MTF_Data_struct &bb[])                      // §13 phase table (Python thresholds)
{
   int n = MathMin(g_dbbw_n, PH_LOOKBACK);
   if(n < 2) return PH_NONE;
   double cur = g_dbbw_ring[0];
   double prev = (n >= 2) ? g_dbbw_ring[1] : cur;

   int h4mid = bb[4].BB_diffMid_Trend[LA];
   int h4stg = bb[4].BBW_stage[LA];
   int h4ud  = bb[4].BBUpDn_state[LA];

   // PH_1: directional trend — 3+ recent bars positive, stage>=500      // §13 Phase 1
   if(n >= 3 && h4stg >= 500) {
      bool allPos = (g_dbbw_ring[0] > 0) && (g_dbbw_ring[1] > 0) && (g_dbbw_ring[2] > 0);
      if(allPos) return PH_1;
   }

   // H4 in SQZ → Phase 4                                                // §13 Phase 4
   if(IsSQZ(h4stg)) return PH_4;

   // PH_5: explosive breakout — diffBBW sharply positive after near-zero // §13 Phase 5
   if(MathAbs(prev) < 5 && cur > 15 && h4ud == 1)                     return PH_5;
   if(prev < 0 && cur > 20 && h4ud == 1)                              return PH_5;

   // PH_6: alternating diffBBW over lookback                            // §13 Phase 6
   if(n >= 4) {
      int alternations = 0;
      for(int i=0; i<3 && i+1<n; i++) {
         bool iPos = g_dbbw_ring[i] > 0;
         bool iP1Pos = g_dbbw_ring[i+1] > 0;
         if(iPos != iP1Pos) alternations++;
      }
      if(alternations >= 3) return PH_6;
   }

   // PH_3*: negative diffBBW (compression)                               // §13 Phase 3
   if(cur < -5) {
      if(h4mid == 3) return PH_3A;                                     // symmetric
      return PH_3B_INTO;                                               // asymmetric — trending INTO
   }

   // PH_3B_OUT: diffBBW near zero → positive, H4 exiting shrink          // §13 3b-OUT
   if(-5 <= cur && cur <= 5 && (h4ud == 1 || h4ud == 3)) {
      if(prev < -10) return PH_3B_OUT;
   }

   // PH_2: diffBBW transitioning pos→zero (pre-SQZ zigzag)               // §13 Phase 2
   if(cur > 0 && cur < 15 && h4stg >= 500) return PH_2;

   // PH_3A default: H4 mid=3 with fly stage
   if(h4mid == 3 && h4stg >= 500) return PH_3A;

   // Fallback
   if(cur > 0) return PH_2;
   return PH_1;
}

// ── D1 helpers (mirrors Python classify_d1_state) ────────────────────
string D1Dir(BB_MTF_Data_struct &bb[]) {
   int m = bb[5].BB_diffMid_Trend[LA];
   if(m==1||m==5) return "bullish";
   if(m==2||m==4) return "bearish";
   int stg = bb[5].BBW_stage[LA];
   if(stg==511||stg==512) return "bullish";
   if(stg==521||stg==522) return "bearish";
   return "neutral";
}

ScenarioState IdentifyScenario(BB_MTF_Data_struct &bb[], double &close_prices[])
{
   ScenarioState s;
   s.scenario=SC_NONE; s.phase=PH_NONE;
   s.cas_shrinkTF=-1;  s.cas_sqzCount=0;
   s.b1_block=false;   s.b2_pink=false;
   s.container_tf=-1;  s.container_dir=0; s.container_diffbbw=0; s.priceloc=0;
   s.pivot_substate=0; // 0=N/A 1=PIVOT-PENDING 2=G-REVERSAL

   // ── diffBBW_H4: push to ring + history ────────────────────────────
   double dbbw_h4 = ADiffBBW(bb, 4);
   RingPush(dbbw_h4);
   DbbwH4HistPush(dbbw_h4);

   // ── §12d decoders ────────────────────────────────────────────────
   for(int tf=1; tf<=5; tf++)                                          // §12d cas_shrinkTF (M15..D1)
      if(IsShrink(bb[tf].BBW_stage[LA])) s.cas_shrinkTF = tf;         // highest wins
   for(int tf=0; tf<=3; tf++)                                          // §12d cas_sqzCount (M5..H1)
      if(IsSQZ(bb[tf].BBW_stage[LA])) s.cas_sqzCount++;

   bool m15sqz = IsSQZ(bb[1].BBW_stage[LA]);
   bool m30sqz = IsSQZ(bb[2].BBW_stage[LA]);
   s.b2_pink  = (m15sqz && m30sqz);                                    // Part 5 B2
   s.b1_block = (bb[1].BB_diffMid_Trend[LA] >= 3);                     // Part 5 B1

   // ── LTF shrink (M15..H1 only — Python Decision 5/6 scope) ────────
   int ltf_shrinkTF = -1;
   for(int tf=1; tf<=3; tf++)
      if(IsShrink(bb[tf].BBW_stage[LA])) ltf_shrinkTF = tf;

   // ── Part 6 Step 2b container (W1 addendum) ────────────────────────
   for(int tf=5; tf>=1; tf--) {                                       // highest committed fly
      int stg = bb[tf].BBW_stage[LA];
      int mid = bb[tf].BB_diffMid_Trend[LA];
      double db = ADiffBBW(bb, tf);
      bool committed = IsFly(stg) && (mid==1||mid==2) && (db >= -0.3);  // diffBBW-primary V4, abs formula
      if(committed) { s.container_tf=tf; s.container_dir=mid; s.container_diffbbw=db; break; }
   }
   if(s.container_tf > 0) {                                           // PriceLoc vs container
      double up = ABBUpper(bb, s.container_tf);
      double lo = ABBLower(bb, s.container_tf);
      double w  = up - lo;
      double px = close_prices[LA];
      double band = 0.15*w;                                           // "at" threshold
      if(px > up)              s.priceloc = +2;
      else if(px > up-band)    s.priceloc = +1;
      else if(px < lo)         s.priceloc = -2;
      else if(px < lo+band)    s.priceloc = -1;
      else                     s.priceloc = 0;
   }

   // ── §13 phase ────────────────────────────────────────────────────
   s.phase = ClassifyPhase(bb);

   // ── CHECK HTF: H4 × D1 (§12) — diffBBW PRIMARY (EDIT V4) ─────────
   int  h4stg  = bb[4].BBW_stage[LA];
   int  h4mid  = bb[4].BB_diffMid_Trend[LA];
   int  h4ud   = bb[4].BBUpDn_state[LA];
   int  d1stg  = bb[5].BBW_stage[LA];
   int  d1mid  = bb[5].BB_diffMid_Trend[LA];
   string d1dir = D1Dir(bb);

   // H4 direction
   int h4_dir = 0;
   if(h4mid==1||h4mid==5) h4_dir=1;
   else if(h4mid==2||h4mid==4) h4_dir=2;

   // §12 classification — thresholds from Python (absolute diffBBW)
   bool h4_fly    = IsFly(h4stg) && (h4mid==1||h4mid==2||h4mid==3) && dbbw_h4 > -15;
   bool h4_shrink = (IsShrink(h4stg) && !IsSQZ(h4stg)) || (dbbw_h4 < -20 && !IsSQZ(h4stg));
   bool h4_sqz    = IsSQZ(h4stg) || (MathAbs(dbbw_h4) <= 0.2 && h4mid==3 && !h4_fly);
   bool d1_fly    = IsFly(d1stg) && (d1mid==1||d1mid==2||d1mid==4||d1mid==5);

   // ── Step 3: Early F-tier — H4 exiting compression ─────────────────
   // Fires before G/E4 — H4 may still be in SQZ/shrink stage but bands
   // are expanding. OOS-validated: 7/7 episodes in Jan-Apr OOS.
   if(s_dbbwH4_hist_n >= 2) {
      double recent_dbbw = s_dbbwH4_hist[0];
      double prev_dbbw   = s_dbbwH4_hist[1];
      if(h4_fly && h4ud == 1 && recent_dbbw > 15 && prev_dbbw < 10) {
         bool h4_bull = (h4mid==1||h4mid==5);
         if(d1dir=="bullish" && h4_bull) {
            // F3 if 3+ consecutive bars positive diffBBW
            if(g_dbbw_n >= 3 && g_dbbw_ring[0]>0 && g_dbbw_ring[1]>0 && g_dbbw_ring[2]>0) {
               s.scenario = SC_F3; s.info = "F3 — HTF confirmed expansion";
               return s;
            }
            // F2 if M30 confirms
            if(bb[2].BBUpDn_state[LA] == 1) {
               s.scenario = SC_F2; s.info = "F2 — MTF confirmed expansion";
               return s;
            }
            // F1 — LTF expansion only
            s.scenario = SC_F1; s.info = "F1 — LTF expansion";
            return s;
         }
      }
   }

   // ── Step 4: H4 SQZ → G-tier (Direction pivot) ─────────────────────
   // OOS-UNVALIDATED: G-reversal — fired 0 times on Jan-Apr OOS
   // (7 F, 0 G episodes). Provisional until a reversal-episode dataset
   // validates it. Do not trust the G-resolution branch live.
   if(h4_sqz) {
      // OOS-UNVALIDATED: G-reversal/discriminator
      double m5db = ADiffBBW(bb,0);
      bool m5_ud_break = (m5db > 0.3);                                // M5 expansion proxy (Python: > 0.3, abs formula)
      if(!m5_ud_break) {
         if(d1_fly && d1dir=="bearish" && (h4mid==2||h4mid==4))
            s.scenario = SC_G1;                                       // OOS-UNVALIDATED
         else if(d1_fly)
            s.scenario = SC_G2;                                       // OOS-UNVALIDATED
         else
            s.scenario = SC_G3;                                       // OOS-UNVALIDATED
      } else {
         int m5mid = bb[0].BB_diffMid_Trend[LA];
         bool sameAsD1 = ((d1mid==1||d1mid==5) && (m5mid==1||m5mid==5)) ||
                         ((d1mid==2||d1mid==4) && (m5mid==2||m5mid==4));
         if(d1_fly) {
            s.scenario = sameAsD1 ? SC_G1 : SC_G2;                    // OOS-UNVALIDATED
         } else
            s.scenario = SC_G3;                                       // OOS-UNVALIDATED
      }
      if(s.phase==PH_6) s.scenario = SC_G4;                           // OOS-UNVALIDATED, extended whipsaw
      // G-tier sub-state for display (one-place computation — label reads this)
      s.pivot_substate = m5_ud_break ? 2 : 1;                         // 1=PIVOT-PENDING 2=G-REVERSAL
      // Update prev H1-SQZ for next call
      s.cas_shrinkTF = s.cas_shrinkTF; s.cas_sqzCount = s.cas_sqzCount;
      return s;
   }

   // ── Step 5: H4 shrink → E4 (after G-tier, since SQZ takes priority) ──
   if(h4_shrink) {
      s.scenario = SC_E4;
      s.info = "E4 — HTF compressing";
      return s;
   }

   // ── Step 6: Compression routing (before h4_fly — Cluster 1 fix) ──
   // confirmed_compression = cas_sqzCount>=1 OR diffBBW-confirmed LTF shrink
   bool confirmed_compression = (s.cas_sqzCount >= 1 ||
                                (ltf_shrinkTF >= 1 && dbbw_h4 < 30));
   if(confirmed_compression) {
      // ── Decision 5: H1-SQZ prior-bar → E/B-tier ────────────────────
      bool h1_sqz_now = IsSQZ(bb[3].BBW_stage[LA]);

      // Established (2+ bars H1-SQZ) → E-tier
      if(h1_sqz_now && s_prevH1Sqz) {
         if(m15sqz && m30sqz) {
            s.scenario = SC_E2; s.info = "E2 — H1-SQZ established, M15+M30 SQZ";
            return s;
         }
         s.scenario = SC_E1; s.info = "E1 — H1-SQZ established";
         return s;
      }

      // ── Decision 6: H1-SQZ recovery → E1 ───────────────────────────
      // H1 just exited SQZ but prior bar was SQZ, compression persists
      if(s_prevH1Sqz && !h1_sqz_now && ltf_shrinkTF >= 1) {
         s.scenario = SC_E1; s.info = "E1 — H1-SQZ recovery, compression persists";
         return s;
      }

      // Onset — H1 first-bar SQZ → B3
      if(h1_sqz_now) {
         s.scenario = SC_B3; s.info = "B3 — H1-SQZ onset";
         return s;
      }

      // ── Decision 2: transient mid-TF SQZ, H4 flying → A-tier ───────
      if(h4_fly && dbbw_h4 > 5 && ltf_shrinkTF == -1 && !s_prevH1Sqz) {
         int m5stg = bb[0].BBW_stage[LA];
         if(s.cas_sqzCount == 1 && !m15sqz && !IsSQZ(m5stg)) {
            bool d1_aligned = (d1stg >= 500 && d1dir != "neutral");
            if(d1_aligned) {
               bool h4_up = (h4_dir == 1);
               bool d1_up = (d1dir == "bullish");
               if(h4_up == d1_up) {
                  s.scenario = SC_A1; s.info = "A1 — mid-TF SQZ, M15+M5 flying, D1 aligned";
                  return s;
               }
            }
            s.scenario = SC_A2; s.info = "A2 — mid-TF SQZ, M15+M5 flying, D1 not aligned";
            return s;
         }
      }

      // ── E-tier: cas_sqzCount>=2 ────────────────────────────────────
      if(s.cas_sqzCount >= 2) {
         if(s.b2_pink) {
            s.scenario = SC_E2; s.info = "E2 — M15+M30 both SQZ";
            return s;
         }
         s.scenario = SC_E1; s.info = "E1 — LTF SQZ";
         return s;
      }

      // ── B-tier: ltf_shrinkTF>=1, keyed by max(shrink, sqz) depth ───
      if(ltf_shrinkTF >= 1) {
         int deepest_sqz_TF = -1;
         for(int tf=0; tf<=3; tf++)
            if(IsSQZ(bb[tf].BBW_stage[LA])) deepest_sqz_TF = tf;
         int max_depth = (ltf_shrinkTF > deepest_sqz_TF) ? ltf_shrinkTF : deepest_sqz_TF;

         // B-tier decoder lookup table
         if(max_depth==1 && s.cas_sqzCount<=1) { s.scenario=SC_B1; return s; }
         if(max_depth==2 && s.cas_sqzCount<=1) { s.scenario=SC_B2; return s; }
         if(max_depth==3 && s.cas_sqzCount<=1) { s.scenario=SC_B3; return s; }
         s.scenario = SC_B3; s.info = "B3 — LTF shrink";
         return s;
      }

      // ── A2: SQZ without LTF shrink (safety net) ────────────────────
      s.scenario = SC_A2; s.info = "A2 — SQZ without LTF shrink";
      return s;
   }

   // ── Step 7: H4 flying → A-tier (no-compression cases only) ────────
   if(h4_fly) {
      // A1: D1 aligned
      if(d1stg >= 500 && d1dir != "neutral") {
         bool h4_up = (h4_dir == 1);
         bool d1_up = (d1dir == "bullish");
         if(h4_up == d1_up) {
            s.scenario = SC_A1; s.info = "A1 — H4+D1 fly aligned";
            return s;
         }
      }
      // A2: D1 not aligned
      s.scenario = SC_A2; s.info = "A2 — H4 fly, D1 not aligned";
      return s;
   }

   // ── Step 8: Default fallback ─────────────────────────────────────
   s.scenario = SC_A2; s.info = "default — conservative";

   // ── Update prev H1-SQZ for next call (Decision 5/6) ───────────────
   s_prevH1Sqz = IsSQZ(bb[3].BBW_stage[LA]);

   return s;
}

//═══════════════════════════════════════════════════════════════════
// LAYER 2 — PredictNext                              (doc Part 4)
// Salvaged TF_DirectionScore skeleton from TofyTrade4 (verbatim core)
//═══════════════════════════════════════════════════════════════════
int TF_DirectionScore(int stage, int mid, int prev_stage, int prev_mid)   // kept verbatim
{
   int stg = 0;
   if     (stage==511) stg = +3; else if(stage==512) stg = +2; else if(stage==513) stg = +1;
   else if(stage==521) stg = -3; else if(stage==522) stg = -2; else if(stage==523) stg = -1;
   int mid_b = 0;
   if(mid==1) mid_b=+2; else if(mid==5) mid_b=+1; else if(mid==4) mid_b=-1; else if(mid==2) mid_b=-2;
   int stg_t = 0;
   bool prev_sqz=(prev_stage>=400&&prev_stage<500);
   bool prev_fu=(prev_stage==511||prev_stage==512), prev_fd=(prev_stage==521||prev_stage==522);
   bool cur_fu=(stage==511||stage==512), cur_fd=(stage==521||stage==522);
   if(prev_sqz&&cur_fu) stg_t=+3; else if(prev_sqz&&cur_fd) stg_t=-3;
   else if(prev_fd&&cur_fu) stg_t=+3; else if(prev_fu&&cur_fd) stg_t=-3;
   else if(prev_fu&&stage==513) stg_t=-1; else if(prev_fd&&stage==523) stg_t=+1;
   else if(prev_stage==513&&cur_fu) stg_t=+2; else if(prev_stage==523&&cur_fd) stg_t=-2;
   int mid_t = 0;
   if(prev_mid==3&&mid==1) mid_t=+2; else if(prev_mid==3&&mid==2) mid_t=-2;
   else if(prev_mid==2&&mid==1) mid_t=+3; else if(prev_mid==1&&mid==2) mid_t=-3;
   else if(prev_mid==1&&mid==3) mid_t=-1; else if(prev_mid==2&&mid==3) mid_t=+1;
   else if(prev_mid==3&&mid==5) mid_t=+1; else if(prev_mid==3&&mid==4) mid_t=-1;
   int raw = stg+mid_b+stg_t+mid_t;
   if(raw>8) raw=8; if(raw<-8) raw=-8;
   return raw;
}

Prediction PredictNext(ScenarioState &s, BB_MTF_Data_struct &bb[])
{
   Prediction p; p.direction=0; p.target_tf=-1; p.timeline_bars=0;
   p.next_scenario=SC_NONE; p.confidence=0; p.reversal=false; p.info="";

   int sc[7];
   for(int tf=1; tf<=6; tf++)
      sc[tf] = TF_DirectionScore(bb[tf].BBW_stage[LA],  bb[tf].BB_diffMid_Trend[LA],
                                 bb[tf].BBW_stage[LA_1],bb[tf].BB_diffMid_Trend[LA_1]);
   // diffBBW damping (Part 4 Rule 5 adjust): expanding reinforces, contracting damps
   for(int tf=1; tf<=6; tf++) {
      double db = ADiffBBW(bb, tf);
      if(db < -0.5) sc[tf] = (int)MathRound(sc[tf]*0.5);              // contracting halves conviction
      else if(db > 1.0 && sc[tf]!=0) sc[tf] += (sc[tf]>0?+1:-1);      // strong expansion +1
   }
   int ltf = sc[1]*1, mtf = sc[2]*2+sc[3]*2, htf = sc[4]*3+sc[5]*2+sc[6]*1;   // weights kept
   int total = ltf+mtf+htf;
   if(total>=22) p.direction=1; else if(total<=-22) p.direction=2;     // threshold kept
   int a=MathAbs(total);
   p.confidence = (a>=66)?95:(a>=44)?80:(a>=22)?60:25;
   p.reversal = (htf>=18 && ltf+mtf<=-12)||(htf<=-18 && ltf+mtf>=12);
   if(p.reversal) p.confidence=MathMin(p.confidence,65);

   // scenario/phase gating (Part 4 Rule 5): PH_4 / G4 force band None
   if(s.phase==PH_4 || s.scenario==SC_G4 || s.scenario==SC_E2) { p.confidence=0; p.direction=0; }
   if(s.scenario==SC_G2 || s.scenario==SC_C1) p.confidence=MathMin(p.confidence,60);  // counter-D1 cap

   // target (Part 4 Rule 2): container primary, scenario fallback
   p.target_tf = (s.container_tf>0) ? s.container_tf :
                 (s.scenario==SC_B1||s.scenario==SC_D1s||s.scenario==SC_D2s) ? 2 :
                 (s.scenario==SC_B2) ? 3 : 4;

   // timeline (Part 4 Rule 3, coarse M5 bars)
   p.timeline_bars = (s.phase==PH_5)?24:(s.phase==PH_2)?96:(s.phase==PH_3A||s.phase==PH_3B_INTO)?60:
                     (s.phase==PH_6)?192:48;

   // next scenario (Part 4 Rule 4, principal edges)
   switch(s.scenario){
      case SC_A1: case SC_A2: p.next_scenario=SC_B1; break;
      case SC_B1:             p.next_scenario=SC_B2; break;
      case SC_B2:             p.next_scenario=SC_B3; break;
      case SC_B3:             p.next_scenario=SC_E1; break;
      case SC_E1:             p.next_scenario=SC_E2; break;
      case SC_E2: case SC_E3L:p.next_scenario=SC_E4; break;
      case SC_E4:             p.next_scenario= (ADiffBBW(bb,5)<-0.3)?SC_G3:SC_G2; break;
      case SC_G1:             p.next_scenario=SC_F2; break;
      case SC_G2:             p.next_scenario=SC_C1; break;
      case SC_F1:             p.next_scenario=SC_F2; break;
      case SC_F2:             p.next_scenario=SC_F3; break;
      case SC_F3:             p.next_scenario=SC_A1; break;
      case SC_C1:             p.next_scenario=SC_C2; break;
      case SC_C2:             p.next_scenario=SC_A1; break;
      case SC_D1s:            p.next_scenario=SC_D2s; break;
      case SC_D2s:            p.next_scenario=SC_D3s; break;
      case SC_D3s:            p.next_scenario=SC_A1; break;
      default:                p.next_scenario=SC_NONE;
   }
   p.info = KVi("tot",total)+KVi("htf",htf)+KVi("mtf",mtf)+KVi("ltf",ltf);
   return p;
}

//═══════════════════════════════════════════════════════════════════
// LAYER 3 — DecideAction                              (doc Part 5)
// Firing matrix: nothing fires unless the (scenario,phase) row arms it.
//═══════════════════════════════════════════════════════════════════
// matrix ceilings (Part 5 + gate-rewrite Step 4)
double MatrixCeiling(SCENARIO sc, PHASE ph)
{
   switch(sc){
      case SC_A1: return 1.00;  case SC_A2: return 0.75;  case SC_A3: return 0.0;
      case SC_B1: return 0.75;  case SC_B2: return 0.50;  case SC_B3: return 0.25;
      case SC_E1: return 0.0;   case SC_E2: return 0.0;
      case SC_E3L:return 0.50;  case SC_E4: return 0.0;
      case SC_G1: return 0.75;  case SC_G2: return 0.25;
      case SC_G3: return 0.0;   case SC_G4: return 0.25;          // PH_6 legs
      case SC_D1s:return 0.0;   case SC_D2s:return 0.75;  case SC_D3s:return 1.00;
      case SC_F1: return 0.0;   case SC_F2: return 0.75;  case SC_F3: return 1.00;
      case SC_C1: return 0.25;  case SC_C2: return 1.00;  case SC_C3: return 0.50;
      default:    return 0.0;
   }
}
double ConfSize(int conf)                                          // Part 4 Rule 5 → Part 5 size
{  return (conf>=90)?1.0:(conf>=75)?0.75:(conf>=60)?0.5:(conf>=45)?0.25:0.0; }

double DecoderSize(ScenarioState &s)                               // §12d combined decoder // V5
{
   if(s.b2_pink || s.cas_sqzCount>=3) return 0.0;
   if(s.cas_shrinkTF==3 && s.cas_sqzCount>=2) return 0.0;          // E2 row
   if(s.cas_sqzCount>=1 && s.cas_shrinkTF>=2) return 0.25;         // "B2 late → E1" — the 03.03 row
   if(s.cas_shrinkTF==3) return 0.25;
   if(s.cas_shrinkTF==2) return 0.50;
   if(s.cas_shrinkTF==1) return 0.75;
   return 1.0;
}

// E3 — boundary fade entry, 6 confinement checks (Part 5 E3; ex-G0b filters)
bool E3Check(ScenarioState &s, BB_MTF_Data_struct &bb[], int dir, string &whyfail, int &q)
{
   q = 65;
   int h4mid = bb[4].BB_diffMid_Trend[LA];
   // chk1 lean — doc says H4 mid 4/5; V1 allows both-direction phases when mid=3
   bool chk1 = (h4mid!=3) || (s.phase==PH_3A || s.phase==PH_6);     // resolution flagged for replay
   if(!chk1){ whyfail="chk1-noLean"; return false; }
   bool chk2 = !(IsSQZ(bb[1].BBW_stage[LA]) && IsSQZ(bb[2].BBW_stage[LA]));   // SQZ lock
   if(!chk2){ whyfail="chk2-sqzlock"; return false; }
   int m5mid = bb[0].BB_diffMid_Trend[LA];
   bool chk3 = (dir==1) ? (m5mid==1||m5mid==5) : (m5mid==2||m5mid==4);        // M5 confirm
   if(!chk3){ whyfail="chk3-m5"; return false; }
   int m30mid = bb[2].BB_diffMid_Trend[LA];
   bool chk4 = !((dir==1&&m30mid==2)||(dir==2&&m30mid==1));                   // M30 not opposing
   if(!chk4){ whyfail="chk4-m30opp"; return false; }
   bool chk5 = !s.b2_pink;                                                    // pink
   if(!chk5){ whyfail="chk5-pink"; return false; }
   if(s.container_dir==dir) q += 10;                                          // with-lean bonus
   if((dir==1&&ADiffBBW(bb,0)>0.3)||(dir==2&&ADiffBBW(bb,0)>0.3)) q += 10;    // M5 energy
   bool chk6 = (q >= 60);                                                     // quality floor
   if(!chk6){ whyfail="chk6-q"; return false; }
   whyfail=""; return true;
}

// M15 transition detector (flip-path entries E1/E2/E5 — slim port of TT4 G5 core)
int DetectFlip(BB_MTF_Data_struct &bb[], int trigTF, int &quality)
{
   int cur  = bb[trigTF].BB_diffMid_Trend[LA];
   int prev = bb[trigTF].BB_diffMid_Trend[LA_1];
   int prev2= bb[trigTF].BB_diffMid_Trend[LA_2];
   quality = 0;
   int dir = 0;
   if((prev==3||prev2==3) && cur==1) { dir=1; quality=70+trigTF*10; }          // FLAT→UP
   else if((prev==3||prev2==3) && cur==2) { dir=2; quality=70+trigTF*10; }     // FLAT→DN
   else if(prev==2 && cur==1) { dir=1; quality=75+trigTF*5; }                  // direct rev
   else if(prev==1 && cur==2) { dir=2; quality=75+trigTF*5; }
   if(dir!=0) {
      int cTF=MathMin(trigTF+1,4);
      int cmid=bb[cTF].BB_diffMid_Trend[LA], cstg=bb[cTF].BBW_stage[LA];
      if((dir==1&&cmid==1&&IsFlyUp(cstg))||(dir==2&&cmid==2&&IsFlyDn(cstg))) quality+=10;
      if(ADiffBBW(bb,cTF) > 0.3) quality+=5;                                   // V4: expansion confirm
   }
   return dir;
}

TradeAction DecideAction(ScenarioState &s, Prediction &p, BB_MTF_Data_struct &bb[],
                         ATRSLBUF_struct &ATRSL1BUF, double &close_prices[],
                         int BUYS, int SELLS)
{
   TradeAction a; a.act=0; a.condition_id="WAIT"; a.size_mult=0; a.stop_price=0; a.info="";
   bool flat = (BUYS+SELLS==0);
   bool holdingBuy=(BUYS>0), holdingSell=(SELLS>0);
   double px = close_prices[LA];

   //── EXITS first (position open) ────────────────────────────────
   if(!flat) {
      int tdir = holdingBuy?1:2;
      // X1: target band reached (Part 5 X1; EDIT V3 primary in zigzag)
      if(p.target_tf>0) {
         double up=ABBUpper(bb,p.target_tf), lo=ABBLower(bb,p.target_tf);
         if((holdingBuy && px>=up) || (holdingSell && px<=lo)) {
            a.act=7; a.condition_id="X1";
            SigEvt("X1", KV("dir",holdingBuy?"BUY":"SELL")+KV("tgt",TFName(p.target_tf))+KVd("hit",px,1));
            return a;
         }
      }
      // X2 qualified (Part 5 X2 + EDIT W1c): M15 fade + container cracking
      int m15mid=bb[1].BB_diffMid_Trend[LA];
      bool fade = (holdingBuy && m15mid>=3 && bb[1].BB_diffMid_Trend[LA_1]==1) ||
                  (holdingSell&& m15mid>=3 && bb[1].BB_diffMid_Trend[LA_1]==2);
      bool zigzag = (s.phase==PH_2||s.phase==PH_3A||s.phase==PH_3B_INTO||s.phase==PH_3B_OUT||s.phase==PH_6);
      if(fade) {
         string reason="";
         bool crack = (s.container_diffbbw<=0.0) ||
                      (s.container_tf>0 && bb[s.container_tf].BB_diffMid_Trend[LA]>=3);
         bool invalid = (s.container_tf>0) &&
                        ((holdingBuy && IsFlyDn(bb[s.container_tf].BBW_stage[LA])) ||
                         (holdingSell&& IsFlyUp(bb[s.container_tf].BBW_stage[LA])));
         if(!zigzag)            reason="trend-fade";        // PH_1: X2 primary  // V3
         else if(crack)         reason="container-crack";   // W1c (a)
         else if(invalid)       reason="invalidated";       // W1c (c)
         // W1c (b) stall handled by 3-consecutive-flat proxy:
         else if(bb[1].BB_diffMid_Trend[LA_1]>=3 && bb[1].BB_diffMid_Trend[LA_2]>=3) reason="stall3";
         if(reason!="") {
            a.act=7; a.condition_id="X2";
            SigEvt("X2", KV("dir",holdingBuy?"BUY":"SELL")+KV("reason",reason));   // reason MANDATORY
            return a;
         }
         // fade unqualified in zigzag → HOLD (the 03.17-03.19 fix)              // V3
      }
      return a;                                              // hold
   }

   //── ENTRIES (flat) — firing matrix arms by (scenario, phase) ───
   double ceiling = MatrixCeiling(s.scenario, s.phase);
   if(ceiling <= 0.0) { a.condition_id="WAIT"; return a; }

   // ASSERTIONS (gate-rewrite: log+suppress, never control flow)
   if(s.b2_pink)        { SigEvt("ASSERT",KV("rule","B2")+KV("sc",ScenarioName(s.scenario))); return a; }
   if(s.cas_sqzCount>=3 && s.scenario!=SC_E3L)
                        { SigEvt("ASSERT",KV("rule","B4")+KV("sc",ScenarioName(s.scenario))); return a; }

   bool zigzagPh = (s.phase==PH_2||s.phase==PH_3A||s.phase==PH_3B_INTO||s.phase==PH_3B_OUT||s.phase==PH_6);

   // E3 primary in zigzag phases (EDIT V2) — boundary fade at container band
   if(zigzagPh && s.container_tf>0 && (s.priceloc==+1||s.priceloc==-1)) {
      int dir = (s.priceloc==+1) ? 2 : 1;                    // fade away from touched band
      // 3B-INTO: favour trending side; counter side allowed at 0.25 (matrix note)
      double sideCeil = ceiling;
      if(s.phase==PH_3B_INTO && s.container_dir!=0 && dir!=s.container_dir) sideCeil=MathMin(sideCeil,0.25);
      if(s.phase==PH_3B_OUT  && s.container_dir!=0 && dir==s.container_dir) {} // recovery side ok
      string why; int q;
      if(E3Check(s, bb, dir, why, q)) {
         a.act = (dir==1)?1:2; a.condition_id="E3";
         a.size_mult = MathMin(MathMin(sideCeil, ConfSize(MathMax(p.confidence,q))), DecoderSize(s));   // V5
         a.stop_price = GetATRSLStop(ATRSL1BUF, dir);
         SigEvt("E3", KV("dir",dir==1?"BUY":"SELL")+KVi("q",q)+KVd("sz",a.size_mult)+KV("loc",IntegerToString(s.priceloc)));
         return a;
      } else if(why!="") SigEvt("E3CHK", KV("fail",why)+KV("dir",dir==1?"BUY":"SELL"));
   }

   // Flip-path entries: E1/E2 (PH_1/2), E5 (PH_5), E6 (F3/C2)        // Part 5 + V2 table
   bool flipArmed = (s.phase==PH_1 || s.phase==PH_2 || s.phase==PH_5);
   if(flipArmed && !s.b1_block) {                            // B1: flips need a flip — M15 mid<3 by definition
      int q=0; int dir = DetectFlip(bb, 1, q);
      if(dir!=0 && dir==p.direction && p.confidence>=45) {
         string id = (s.scenario==SC_F3||s.scenario==SC_C2) ? "E6" :
                     (s.phase==PH_5) ? "E5" :
                     (s.scenario==SC_A2) ? "E2" : "E1";
         a.act=(dir==1)?1:2; a.condition_id=id;
         a.size_mult = MathMin(MathMin(ceiling, ConfSize(p.confidence)), DecoderSize(s));               // V5
         a.stop_price= GetATRSLStop(ATRSL1BUF, dir);
         SigEvt(id, KV("dir",dir==1?"BUY":"SELL")+KVi("q",q)+KVi("conf",p.confidence)+KVd("sz",a.size_mult));
         return a;
      }
   }
   // E4-ARM informational (E3 loading state)                          // Part 5 E4
   if(s.scenario==SC_E3L) {
      int m30mid=bb[2].BB_diffMid_Trend[LA];
      SigEvt("E4ARM", KV("dir",(m30mid==1||m30mid==5)?"BUY":(m30mid==2||m30mid==4)?"SELL":"NEUTRAL"));
   }
   return a;
}

//═══════════════════════════════════════════════════════════════════
// CSV trade logger — kept from TofyTrade4 (file prefix bumped)
//═══════════════════════════════════════════════════════════════════
string g_csv_filename = "";
int    g_csv_handle = INVALID_HANDLE;
string g_last_trade_info = "";
int    g_entry_stages[5];
int    g_entry_mids[5];
int    g_entry_atrsl_dir = 0;

void CSV_Init()
{
   string date = StringSubstr(TimeToString(TimeCurrent(),TIME_DATE),0,10);
   StringReplace(date, ".", "-");
   g_csv_filename = "TofyTrade5_" + date + ".csv";
   g_csv_handle = FileOpen(g_csv_filename, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(g_csv_handle == INVALID_HANDLE) { Print("CSV_Init: cannot open ", g_csv_filename); return; }
   FileWrite(g_csv_handle,
      "ticket","type","open_time","close_time","open_price","close_price","lots",
      "profit_usd","profit_pips","condition_id","sl_at_entry",
      "entry_M5_stage","entry_M15_stage","entry_M30_stage","entry_H1_stage","entry_H4_stage",
      "entry_M5_mid","entry_M15_mid","entry_M30_mid","entry_H1_mid","entry_H4_mid",
      "entry_ATRSL_dir",
      "close_M5_stage","close_M15_stage","close_M30_stage","close_H1_stage","close_H4_stage",
      "close_M5_mid","close_M15_mid","close_M30_mid","close_H1_mid","close_H4_mid",
      "close_ATRSL_dir");
   Print("CSV logger started: ", g_csv_filename);
}
void CSV_Close()
{
   if(g_csv_handle != INVALID_HANDLE) { FileClose(g_csv_handle); g_csv_handle=INVALID_HANDLE;
      Print("CSV saved: ", g_csv_filename); }
}
void CSV_CaptureEntryContext(string trade_info, BB_MTF_Data_struct &BB_datas[],
                             ATRSLBUF_struct &ATRSL1BUF)
{
   g_last_trade_info = trade_info;
   for(int i=0;i<=4;i++){ g_entry_stages[i]=(int)BB_datas[i].BBW_stage[LA];
                          g_entry_mids[i]=(int)BB_datas[i].BB_diffMid_Trend[LA]; }
   g_entry_atrsl_dir = ATRSL1BUF.dir;
}
void CSV_LogTrade(int ticket, BB_MTF_Data_struct &BB_datas[],
                  ATRSLBUF_struct &ATRSL1BUF, string trade_info)
{
   if(g_csv_handle == INVALID_HANDLE) return;
   if(!OrderSelect(ticket, SELECT_BY_TICKET)) return;
   string type_str = (OrderType()==OP_BUY) ? "BUY" : "SELL";
   double open_p=OrderOpenPrice(), close_p=OrderClosePrice();
   double profit=OrderProfit()+OrderSwap()+OrderCommission();
   double pips = (OrderType()==OP_BUY) ? (close_p-open_p)/_Point : (open_p-close_p)/_Point;
   string labels = trade_info; StringReplace(labels, ",", ";");
   FileWrite(g_csv_handle,
      IntegerToString(ticket), type_str,
      TimeToString(OrderOpenTime(),TIME_DATE|TIME_SECONDS),
      TimeToString(OrderCloseTime(),TIME_DATE|TIME_SECONDS),
      DoubleToString(open_p,_Digits), DoubleToString(close_p,_Digits),
      DoubleToString(OrderLots(),2), DoubleToString(profit,2), DoubleToString(pips,1),
      labels, DoubleToString(OrderStopLoss(),_Digits),
      IntegerToString(g_entry_stages[0]),IntegerToString(g_entry_stages[1]),
      IntegerToString(g_entry_stages[2]),IntegerToString(g_entry_stages[3]),
      IntegerToString(g_entry_stages[4]),
      IntegerToString(g_entry_mids[0]),IntegerToString(g_entry_mids[1]),
      IntegerToString(g_entry_mids[2]),IntegerToString(g_entry_mids[3]),
      IntegerToString(g_entry_mids[4]),
      IntegerToString(g_entry_atrsl_dir),
      IntegerToString(BB_datas[0].BBW_stage[LA]),IntegerToString(BB_datas[1].BBW_stage[LA]),
      IntegerToString(BB_datas[2].BBW_stage[LA]),IntegerToString(BB_datas[3].BBW_stage[LA]),
      IntegerToString(BB_datas[4].BBW_stage[LA]),
      IntegerToString(BB_datas[0].BB_diffMid_Trend[LA]),IntegerToString(BB_datas[1].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[2].BB_diffMid_Trend[LA]),IntegerToString(BB_datas[3].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[4].BB_diffMid_Trend[LA]),
      IntegerToString(ATRSL1BUF.dir));
}
// NOTE: TofyTrade4's in-EA Stats tracker is intentionally NOT ported —
// superseded by SIG:SIG lines + scripts/sig_to_csv.py (gate-rewrite Step 3).

//═══════════════════════════════════════════════════════════════════
// MAIN ENTRY — exact TofyTrade4 signature preserved
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
   Trade_act=0; Trade_info=""; Trade_lots=baseLot; Trade_sl=0.0;

   static datetime s_lastBar=0;
   static int      s_exitCooldown=0;
   static int      s_barsInTrade=0;
   static int      s_lastTrigTF=1;
   static SCENARIO s_prevSc=SC_NONE;  static PHASE s_prevPh=PH_NONE;
   static bool     s_pivotPending=false; // display-only: PIVOT-PENDING tracker
   static bool     s_initialized=false;
   if(!s_initialized) {
      SigEvt("INIT", KV("ver","31.01")+KV("ruleset","TofyTrade5-v31"));
      s_initialized=true;
   }

   //── INVARIANT 1: EMERGENCY — every call, before anything ────────
   //  (TofyTrade4 defined MAX_FLOATING_LOSS_USD but the 03.03 trade
   //   ran -191: enforcement here is unconditional and first.)
   if(BUYS+SELLS>0) {
      double fl = AFloatingPL();
      if(fl < -MAX_FLOATING_LOSS_USD) {
         Trade_act=7;
         SigEvt("EMERGENCY", KVd("loss",fl));
         Trade_info="SIG:SIG evt:DECISION id:EMERGENCY act:7";
         s_exitCooldown=POST_EXIT_COOLDOWN; s_barsInTrade=0;
         return;
      }
   }

   //── once per confirmed M5 bar ───────────────────────────────────
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur==s_lastBar) { Trade_info=""; return; }
   s_lastBar=cur;
   if(BUYS+SELLS>0) s_barsInTrade++;
   if(s_exitCooldown>0) s_exitCooldown--;

   //── Layer 1 ─────────────────────────────────────────────────────
   ScenarioState s = IdentifyScenario(BB_datas, close_prices);        // RingPush is internal now

   //── Scenario change detection (display-only labels) ─────────────
   // PIVOT-PENDING tracker: during H4 SQZ, show PIVOT-PENDING until
   // the scenario exits G-tier (resolved to F or C).
   // G-reversal (G? with M5 break) shown distinctly in red.
   // Reads s.pivot_substate — computed ONCE inside IdentifyScenario.
   {
      bool gTier = (s.scenario==SC_G1||s.scenario==SC_G2||
                    s.scenario==SC_G3||s.scenario==SC_G4);
      bool pivotNow = (s.pivot_substate == 1); // read from struct, no recompute
      bool gReversal = (s.pivot_substate == 2); // read from struct, no recompute

      if(pivotNow && !s_pivotPending) {
         // Just entered PIVOT-PENDING — draw label
         s_pivotPending = true;
         SigEvt("SC", KV("sc","PIVOT-PENDING")+KV("ph",PhaseName(s.phase))
                     +KVi("pivot",s.pivot_substate)+KVi("casShr",s.cas_shrinkTF)+KVi("casSqz",s.cas_sqzCount)
                     +KV("cont",TFName(s.container_tf))+KVi("loc",s.priceloc)
                     +KVd("dbbwH4",ADiffBBW(BB_datas,4),1));
         DrawGateLabel("PIVOT-PENDING  ph:"+PhaseName(s.phase),
                       BB_datas[2].BB_Mid[LA], BB_datas, TIER_CLR_PIVOT, 2);
         if(LOG_VERBOSE)
            DrawGateLabel("casShr:"+IntegerToString(s.cas_shrinkTF)
                          +" casSqz:"+IntegerToString(s.cas_sqzCount)
                          +" cont:"+TFName(s.container_tf)
                          +" dbbwH4:"+DoubleToString(ADiffBBW(BB_datas,4),1),
                          BB_datas[2].BB_Mid[LA]-20, BB_datas, TIER_CLR_PIVOT, 2);
      } else if(s_pivotPending && !pivotNow) {
         // PIVOT-PENDING cleared — resolve to G? or new scenario
         s_pivotPending = false;
         if(gTier && gReversal) {
            // G-reversal branch — OOS-UNVALIDATED, shown distinctly
            SigEvt("SC", KV("sc",ScenarioName(s.scenario)+"?")+KV("ph",PhaseName(s.phase))
                        +KVi("pivot",s.pivot_substate)+KVi("casShr",s.cas_shrinkTF)+KVi("casSqz",s.cas_sqzCount)
                        +KV("cont",TFName(s.container_tf))+KVi("loc",s.priceloc)
                        +KVd("dbbwH4",ADiffBBW(BB_datas,4),1));
            DrawGateLabel(ScenarioName(s.scenario)+"?  ph:"+PhaseName(s.phase),
                          BB_datas[2].BB_Mid[LA], BB_datas, TIER_CLR_G, 2);
            if(LOG_VERBOSE)
               DrawGateLabel("casShr:"+IntegerToString(s.cas_shrinkTF)
                             +" casSqz:"+IntegerToString(s.cas_sqzCount)
                             +" cont:"+TFName(s.container_tf)
                             +" dbbwH4:"+DoubleToString(ADiffBBW(BB_datas,4),1),
                             BB_datas[2].BB_Mid[LA]-20, BB_datas, TIER_CLR_G, 2);
         } else if(s.scenario!=s_prevSc || s.phase!=s_prevPh) {
            // Resolved to non-G scenario (F/C/etc) — draw new label
            SigEvt("SC", KV("sc",ScenarioName(s.scenario))+KV("ph",PhaseName(s.phase))
                        +KVi("pivot",s.pivot_substate)+KVi("casShr",s.cas_shrinkTF)+KVi("casSqz",s.cas_sqzCount)
                        +KV("cont",TFName(s.container_tf))+KVi("loc",s.priceloc)
                        +KVd("dbbwH4",ADiffBBW(BB_datas,4),1));
            color clr = ScenarioLabelColor(s.scenario);
            DrawGateLabel(ScenarioName(s.scenario)+"  ph:"+PhaseName(s.phase),
                          BB_datas[2].BB_Mid[LA], BB_datas, clr, 2);
            if(LOG_VERBOSE)
               DrawGateLabel("casShr:"+IntegerToString(s.cas_shrinkTF)
                             +" casSqz:"+IntegerToString(s.cas_sqzCount)
                             +" cont:"+TFName(s.container_tf)
                             +" dbbwH4:"+DoubleToString(ADiffBBW(BB_datas,4),1),
                             BB_datas[2].BB_Mid[LA]-20, BB_datas, clr, 2);
         }
      } else if(!s_pivotPending && (s.scenario!=s_prevSc || s.phase!=s_prevPh)) {
         // Normal scenario change (not PIVOT-PENDING)
         SigEvt("SC", KV("sc",ScenarioName(s.scenario))+KV("ph",PhaseName(s.phase))
                     +KVi("pivot",s.pivot_substate)+KVi("casShr",s.cas_shrinkTF)+KVi("casSqz",s.cas_sqzCount)
                     +KV("cont",TFName(s.container_tf))+KVi("loc",s.priceloc)
                     +KVd("dbbwH4",ADiffBBW(BB_datas,4),1));
         color clr = ScenarioLabelColor(s.scenario);
         DrawGateLabel(ScenarioName(s.scenario)+"  ph:"+PhaseName(s.phase),
                       BB_datas[2].BB_Mid[LA], BB_datas, clr, 2);
         if(LOG_VERBOSE)
            DrawGateLabel("casShr:"+IntegerToString(s.cas_shrinkTF)
                          +" casSqz:"+IntegerToString(s.cas_sqzCount)
                          +" cont:"+TFName(s.container_tf)
                          +" dbbwH4:"+DoubleToString(ADiffBBW(BB_datas,4),1),
                          BB_datas[2].BB_Mid[LA]-20, BB_datas, clr, 2);
      }
      s_prevSc=s.scenario; s_prevPh=s.phase;
   }

   //── INVARIANT 2: X4 pink — forced flat ──────────────────────────
   if(s.b2_pink && BUYS+SELLS>0) {                          // Part 5 B2/X4
      Trade_act=7;
      SigEvt("X4", KV("kind","PINK")+KVi("m15bbw",BB_datas[1].BBW_stage[LA])
                  +KVi("m30bbw",BB_datas[2].BBW_stage[LA]));
      DrawGateLabel("[X4-PINK]", close_prices[LA], BB_datas, GATE_CLR_PINK, 1);
      Trade_info="SIG:SIG evt:DECISION id:X4PINK act:7";
      s_exitCooldown=POST_EXIT_COOLDOWN; s_barsInTrade=0;
      return;
   }

   //── Layer 2 (prediction drawn AND consumed) ─────────────────────
   Prediction p = PredictNext(s, BB_datas);
   string pdir=(p.direction==1)?"BUY":(p.direction==2)?"SELL":"NEUTRAL";
   DrawGateLabel("[PRED:"+pdir+":"+IntegerToString(p.confidence)+"]",
                 BB_datas[2].BB_Mid[LA], BB_datas,
                 (p.direction==1)?GATE_CLR_BUY:(p.direction==2)?GATE_CLR_SELL:GATE_CLR_NOISE, 2);

   //── Trailing stop maintenance (tighten-only) — before decisions ─
   if(BUYS+SELLS>0) {
      int tdir = (BUYS>0)?1:2;
      double newsl = GetATRSLStop(ATRSL1BUF, tdir);
      if(newsl>0) {
         // caller applies Trade_sl when nonzero; tighten-only enforced by caller comparing
         // existing SL — emit the trajectory for benchmark item 3 either way
         Trade_sl = newsl;
         SigEvt("SLMOD", KV("dir",tdir==1?"BUY":"SELL")+KVd("sl",newsl,1)
                        +KVi("atrslDir",ATRSL1BUF.dir));
      }
   }

   //── Layer 3 ─────────────────────────────────────────────────────
   TradeAction a = DecideAction(s, p, BB_datas, ATRSL1BUF, close_prices, BUYS, SELLS);

   //── Entry hygiene: cooldown + min-hold (kept from v30) ──────────
   if((a.act==1||a.act==2)) {
      if(s_exitCooldown>0) { a.act=0; a.condition_id="COOLDOWN"; }
      else if(BUYS+SELLS>0 && s_barsInTrade < DynMinHold(s_lastTrigTF))
                           { a.act=0; a.condition_id="MINHOLD"; }
   }

   //── INVARIANT 3: entry-at-target veto (W1 addendum; 03.03 class) ─
   if(a.act==1 && s.priceloc>=+1) {
      SigEvt("VETO", KV("kind","AT-TARGET")+KV("dir","BUY")+KVi("loc",s.priceloc));
      a.act=0; a.condition_id="VETO";
   }
   if(a.act==2 && s.priceloc<=-1) {
      SigEvt("VETO", KV("kind","AT-TARGET")+KV("dir","SELL")+KVi("loc",s.priceloc));
      a.act=0; a.condition_id="VETO";
   }

   //── compose outputs ─────────────────────────────────────────────
   Trade_act  = a.act;
   if(a.act==1 || a.act==2) {
      Trade_lots = NormalizeDouble(MathMax(baseLot*a.size_mult, 0.01), 2);  // V5 sizing APPLIED
      Trade_sl   = a.stop_price;                                            // stop AT entry
      s_barsInTrade=0; s_lastTrigTF=1;
      SigEvt("ORD", KV("dir",a.act==1?"BUY":"SELL")+KV("id",a.condition_id)
                   +KVd("lot",Trade_lots)+KVd("sl",Trade_sl,1)
                   +KV("tgtTF",TFName(p.target_tf))+KVi("conf",p.confidence));
      DrawGateLabel("["+a.condition_id+(a.act==1?":BUY]":":SELL]"),
                    close_prices[LA], BB_datas,
                    (a.act==1)?GATE_CLR_BUY:GATE_CLR_SELL, 1);
      CSV_CaptureEntryContext(a.condition_id, BB_datas, ATRSL1BUF);
   }
   if(a.act==7) { s_exitCooldown=POST_EXIT_COOLDOWN; s_barsInTrade=0; }

   // the ONE per-bar decision record
   Trade_info = "SIG:SIG evt:DECISION"
              + KV("sc",ScenarioName(s.scenario)) + KV("ph",PhaseName(s.phase))
              + KV("id",a.condition_id) + KVi("act",a.act)
              + KVd("sz",a.size_mult) + KVi("conf",p.confidence)
              + KVi("dir",p.direction) + KVd("dbbwH4",ADiffBBW(BB_datas,4),1);
}
//+------------------------------------------------------------------+
// INTEGRATION NOTES for Claude Code (delete after wiring):
// 1. ADAPTER: ADiffBBW now uses ABSOLUTE formula (w_now-w_prev)*100
//    to match the V30.02 log. Verified against log values.
//    ABBUpper/ABBLower field names still need verification.
// 2. AFloatingPL: magic-number filter added (MAGIC_NUMBER=898989).
// 3. Caller must: print Trade_info only when non-empty; apply Trade_sl
//    tighten-only vs the live position SL; treat act semantics
//    identically to TofyTrade4.
// 4. Replay gates before any MT5 backtest:
//    Layer-1 ≥95% vs march2026_expected.csv (GATE 2).
// 5. E3Check chk1 carries a doc conflict resolution (lean vs PH_3A
//    both-direction) — flagged for replay validation, see comment.
// 6. PredictNext diffBBW damping thresholds (-0.5, 1.0) were written
//    for the percentage formula — they are WRONG with the absolute
//    formula. Fix before trusting PredictNext confidence scores.
//+------------------------------------------------------------------+
