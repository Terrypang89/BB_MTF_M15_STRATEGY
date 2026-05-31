#property copyright "Copyright 2024, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "30.02"
#define MIN_HOLD_BARS         3     // minimum M5 bars between entries
#define POST_EXIT_COOLDOWN    5     // M5 bars to block new entries after any act=7 exit
#define MAX_FLOATING_LOSS_USD 50.0  // emergency exit threshold — floating loss deeper than this
#include <TofyIncludeSimple.mqh>

enum ENUM_M5_TRANSITION {
   M5_TRANS_NONE       = 0,
   M5_TRANS_FLAT_TO_UP = 1,   // 3→1 (strongest BUY trigger)
   M5_TRANS_FLAT_TO_DN = 2,   // 3→2 (strongest SELL trigger)
   M5_TRANS_UP_TO_FLAT = 3,   // 1→3 (fading longs — reduce)
   M5_TRANS_DN_TO_FLAT = 4,   // 2→3 (fading shorts — reduce)
   M5_TRANS_UP_TO_DN   = 5,   // 1→2 (direct reversal)
   M5_TRANS_DN_TO_UP   = 6,   // 2→1 (direct reversal)
   M5_TRANS_WEAK_UP    = 7,   // 3→5 (early BUY warning)
   M5_TRANS_WEAK_DN    = 8,   // 3→4 (early SELL warning)
};

struct M5_TransitionResult {
   ENUM_M5_TRANSITION transition;
   int    direction;    // 1=buy, 2=sell, 0=none
   int    quality;      // 0–100 confidence score
   double sizeMulti;    // lot multiplier
   string info;
};

// Position sizing by TF agreement count
double CalcLotSize(int tfAgreeCount, double baseLot) {
   if(tfAgreeCount>=3) return baseLot;
   if(tfAgreeCount==2) return baseLot*0.75;
   if(tfAgreeCount==1) return baseLot*0.5;
   return 0.0;
}

// Count TFs agreeing with trade direction
int CountTFAgreement(BB_MTF_Data_struct &BB_datas[], int direction, int maxTF) {
   int count=0;
   for(int i=0; i<=maxTF; i++) {
      int stage=BB_datas[i].BBW_stage[LA];
      int trend=BB_datas[i].BB_diffMid_Trend[LA];
      if(direction==1 && (stage==511||stage==512) && (trend==1||trend==5)) count++;
      if(direction==2 && (stage==521||stage==522) && (trend==2||trend==4)) count++;
   }
   return count;
}

// ATRSL stop placement
double GetATRSLStop(ATRSLBUF_struct &ATRSL1BUF, int direction) {
   // dir: 0=uptrend  1=downtrend  (no dir=2)
   if(direction==1) {
      // BUY stop = lower band
      // dir=0 (uptrend): ATRSL agrees with BUY  → use ATRSLLower (trailing up)
      // dir=1 (dntrend): ATRSL opposes BUY      → use ATRSLMid   (emergency)
      return (ATRSL1BUF.dir==0) ? ATRSL1BUF.ATRSLLower[LA]
                                 : ATRSL1BUF.ATRSLMid[LA];
   }
   if(direction==2) {
      // SELL stop = upper band
      // dir=1 (dntrend): ATRSL agrees with SELL → use ATRSLUpper (trailing down)
      // dir=0 (uptrend): ATRSL opposes SELL     → use ATRSLMid   (emergency)
      return (ATRSL1BUF.dir==1) ? ATRSL1BUF.ATRSLUpper[LA]
                                 : ATRSL1BUF.ATRSLMid[LA];
   }
   return 0.0;
}

// ── Gate label semantic colors ───────────────────────────────────
#define GATE_CLR_EXIT   clrCrimson      // G0, G0b-PINK, G5-FADE, G6-REV, G0e-MAXLOSS, G8-BNDTGT  — exit all
#define GATE_CLR_BUY    clrLime         // G0b-TOUCH buy, G6-BUY            — buy entry
#define GATE_CLR_SELL   clrOrangeRed    // G0b-TOUCH sell, G6-SELL          — sell entry
#define GATE_CLR_BLOCK  clrRed          // G4-BLOCK                         — hard conflict
#define GATE_CLR_WAIT   clrYellow       // G0b-WAIT                         — cascade waiting
#define GATE_CLR_PINK   clrMagenta      // G0b-PINK                         — pink zone
#define GATE_CLR_LOAD   clrGold         // G6-LOAD, G6-ENTRY                — midline loading
#define GATE_CLR_NOISE  clrDimGray      // G1-FAIL, G7-NEUTRAL, G0b-M15OPP, G0b-M30OPP — noise/skip
#define GATE_CLR_INFO   clrSilver       // G1-OK                            — info only
#define GATE_CLR_AQUA   clrAqua         // reversal BUY / G5 flat→up
#define GATE_CLR_ORANGE clrOrange       // reversal SELL / G5 flat→dn
#define GATE_CLR_H4     clrDarkOrange   // H4 oppose / H4 SQZ               — macro filter

// ── Trend Prediction ──────────────────────────────────────────────
// Predicts next-bar directional bias from stage+mid trajectory across all TFs.
// Uses BB_datas[1..6] = M15/M30/H1/H4/D1/W1.

struct TrendPrediction {
   int    direction;   // 1=BUY, 2=SELL, 0=NEUTRAL
   int    confidence;  // 0-100
   bool   reversal;    // HTF opposes MTF+LTF → counter-trend setup
   int    htf_total;   // weighted score H4×3 + D1×2 + W1×1
   int    mtf_total;   // weighted score H1×2 + M30×2
   int    ltf_total;   // weighted score M15×1
   string info;
};

// Single-TF directional score from stage+mid state and 1-bar transitions. Range: [-8, +8].
int TF_DirectionScore(int stage, int mid, int prev_stage, int prev_mid)
{
   // Stage structural bias
   int stg = 0;
   if     (stage==511)                     stg = +3;
   else if(stage==512)                     stg = +2;
   else if(stage==513)                     stg = +1;
   else if(stage==521)                     stg = -3;
   else if(stage==522)                     stg = -2;
   else if(stage==523)                     stg = -1;

   // Mid momentum bias
   int mid_b = 0;
   if     (mid==1) mid_b = +2;
   else if(mid==5) mid_b = +1;
   else if(mid==4) mid_b = -1;
   else if(mid==2) mid_b = -2;

   // Stage transition bonus (prev → cur)
   int stg_t = 0;
   bool prev_sqz   = (prev_stage>=400 && prev_stage<500);
   bool prev_fly_up = (prev_stage==511||prev_stage==512);
   bool prev_fly_dn = (prev_stage==521||prev_stage==522);
   bool cur_fly_up  = (stage==511||stage==512);
   bool cur_fly_dn  = (stage==521||stage==522);
   if     (prev_sqz    && cur_fly_up)  stg_t = +3;  // SQZ breakout UP
   else if(prev_sqz    && cur_fly_dn)  stg_t = -3;  // SQZ breakout DN
   else if(prev_fly_dn && cur_fly_up)  stg_t = +3;  // direct reversal UP
   else if(prev_fly_up && cur_fly_dn)  stg_t = -3;  // direct reversal DN
   else if(prev_fly_up && stage==513)  stg_t = -1;  // fly weakening (shrink)
   else if(prev_fly_dn && stage==523)  stg_t = +1;  // fly weakening (shrink)
   else if(prev_stage==513 && cur_fly_up) stg_t = +2; // shrink → fly resuming UP
   else if(prev_stage==523 && cur_fly_dn) stg_t = -2; // shrink → fly resuming DN

   // Mid transition bonus (prev → cur)
   int mid_t = 0;
   if     (prev_mid==3 && mid==1) mid_t = +2;  // flat → uptrend
   else if(prev_mid==3 && mid==2) mid_t = -2;  // flat → downtrend
   else if(prev_mid==2 && mid==1) mid_t = +3;  // reversal: dn → up
   else if(prev_mid==1 && mid==2) mid_t = -3;  // reversal: up → dn
   else if(prev_mid==1 && mid==3) mid_t = -1;  // uptrend fading
   else if(prev_mid==2 && mid==3) mid_t = +1;  // downtrend fading
   else if(prev_mid==3 && mid==5) mid_t = +1;  // flat → side-up
   else if(prev_mid==3 && mid==4) mid_t = -1;  // flat → side-dn

   int raw = stg + mid_b + stg_t + mid_t;
   if(raw >  8) raw =  8;
   if(raw < -8) raw = -8;
   return raw;
}

TrendPrediction PredictNextTrend(BB_MTF_Data_struct &BB_datas[])
{
   TrendPrediction pred;
   pred.direction = 0; pred.confidence = 0; pred.reversal = false;
   pred.htf_total = 0; pred.mtf_total = 0; pred.ltf_total = 0;
   pred.info = "";

   // Score each TF using current + 1-bar-prior state
   // BB_datas[1]=M15 [2]=M30 [3]=H1 [4]=H4 [5]=D1 [6]=W1
   int s1 = TF_DirectionScore(BB_datas[1].BBW_stage[LA], BB_datas[1].BB_diffMid_Trend[LA],
                               BB_datas[1].BBW_stage[LA_1], BB_datas[1].BB_diffMid_Trend[LA_1]);
   int s2 = TF_DirectionScore(BB_datas[2].BBW_stage[LA], BB_datas[2].BB_diffMid_Trend[LA],
                               BB_datas[2].BBW_stage[LA_1], BB_datas[2].BB_diffMid_Trend[LA_1]);
   int s3 = TF_DirectionScore(BB_datas[3].BBW_stage[LA], BB_datas[3].BB_diffMid_Trend[LA],
                               BB_datas[3].BBW_stage[LA_1], BB_datas[3].BB_diffMid_Trend[LA_1]);
   int s4 = TF_DirectionScore(BB_datas[4].BBW_stage[LA], BB_datas[4].BB_diffMid_Trend[LA],
                               BB_datas[4].BBW_stage[LA_1], BB_datas[4].BB_diffMid_Trend[LA_1]);
   int s5 = TF_DirectionScore(BB_datas[5].BBW_stage[LA], BB_datas[5].BB_diffMid_Trend[LA],
                               BB_datas[5].BBW_stage[LA_1], BB_datas[5].BB_diffMid_Trend[LA_1]);
   int s6 = TF_DirectionScore(BB_datas[6].BBW_stage[LA], BB_datas[6].BB_diffMid_Trend[LA],
                               BB_datas[6].BBW_stage[LA_1], BB_datas[6].BB_diffMid_Trend[LA_1]);

   // Weighted totals  (max each: H4=24, D1=16, W1=8, H1=16, M30=16, M15=8 → total ±88)
   pred.ltf_total = s1 * 1;
   pred.mtf_total = s2 * 2 + s3 * 2;
   pred.htf_total = s4 * 3 + s5 * 2 + s6 * 1;

   int total = pred.htf_total + pred.mtf_total + pred.ltf_total;

   // Direction: threshold ±22 (~25% of max 88)
   if     (total >=  22) pred.direction = 1;
   else if(total <= -22) pred.direction = 2;

   // Confidence: linear from 25 (±22) to 95 (±88)
   int abs_t = MathAbs(total);
   if     (abs_t >= 66) pred.confidence = 95;
   else if(abs_t >= 44) pred.confidence = 80;
   else if(abs_t >= 22) pred.confidence = 60;
   else                 pred.confidence = 25;

   // Reversal detection: HTF direction strongly opposes MTF+LTF direction
   int ltf_mtf = pred.ltf_total + pred.mtf_total;
   pred.reversal = (pred.htf_total >= 18 && ltf_mtf <= -12) ||
                   (pred.htf_total <= -18 && ltf_mtf >= 12);
   if(pred.reversal) pred.confidence = MathMin(pred.confidence, 65);

   string dir_str = (pred.direction==1) ? "BUY" : (pred.direction==2) ? "SELL" : "NEUTRAL";
   pred.info = "[PRED] "+dir_str+" conf:"+pred.confidence
             + " htf:"+pred.htf_total+" mtf:"+pred.mtf_total+" ltf:"+pred.ltf_total
             + " tot:"+total
             + (pred.reversal ? " REV" : "");

   // ── Draw on chart ────────────────────────────────────────────────
   // Color: lime=continuation BUY, aqua=reversal BUY,
   //        orange-red=continuation SELL, orange=reversal SELL, gray=neutral
   color pred_color;
   if     (pred.direction==1 && !pred.reversal) pred_color = GATE_CLR_BUY;
   else if(pred.direction==1 &&  pred.reversal) pred_color = GATE_CLR_AQUA;
   else if(pred.direction==2 && !pred.reversal) pred_color = GATE_CLR_SELL;
   else if(pred.direction==2 &&  pred.reversal) pred_color = GATE_CLR_ORANGE;
   else                                         pred_color = GATE_CLR_NOISE;

   string rev_pfx = pred.reversal ? "R:" : "";
   string lbl = "[PRED:" + rev_pfx + dir_str + ":" + IntegerToString(pred.confidence) + "]";
   DrawGateLabel(lbl, BB_datas[2].BB_Mid[LA], BB_datas, pred_color, 2);

   return pred;
}

M5_TransitionResult DetectM5Transition(BB_MTF_Data_struct &BB_datas[], double &close_prices[], int triggerTF = 0)
{
   M5_TransitionResult res;
   res.transition = M5_TRANS_NONE;
   res.direction  = 0;
   res.quality    = 0;
   res.sizeMulti  = 0.0;
   res.info       = "";

   int cur   = BB_datas[triggerTF].BB_diffMid_Trend[LA];
   int prev  = BB_datas[triggerTF].BB_diffMid_Trend[LA_1];
   int prev2 = BB_datas[triggerTF].BB_diffMid_Trend[LA_2];

   double close_ref = close_prices[LA];
   double mid_ref   = BB_datas[triggerTF].BB_Mid[LA];
   double mid_ref_1 = BB_datas[triggerTF].BB_Mid[LA_1];
   double diffMid   = BB_datas[triggerTF].BB_diffMid[LA];

   // confirmTF = next higher TF; provides quality boost if it agrees (v22.42)
   int confirmTF  = MathMin(triggerTF + 1, 4);
   int conf_trend = BB_datas[confirmTF].BB_diffMid_Trend[LA];
   int conf_stage = BB_datas[confirmTF].BBW_stage[LA];

   // Base quality scales with trigger TF depth: higher TF = stronger conviction
   int q_base_flat = 70 + triggerTF * 10;  // M5=70, M15=80, M30=90
   int q_base_rev  = 75 + triggerTF * 5;   // M5=75, M15=80, M30=85

   string tfl = "tTF:"+triggerTF+" c:"+cur+" p:"+prev+" p2:"+prev2+" cS:"+conf_stage+" cM:"+conf_trend;

   // ── FLAT → UP (strongest BUY) ─────────────────────────────────
   if((prev==3 || prev2==3) && cur==1) {
      res.transition = M5_TRANS_FLAT_TO_UP;
      res.direction  = 1;
      res.quality    = q_base_flat;
      res.info = "Gate:[G5] "+tfl+" t:flat_up";
      if(mid_ref > mid_ref_1)                      { res.quality+=10; res.info+=" mid+"; }
      if(close_ref > mid_ref && diffMid > 0)        { res.quality+=10; res.info+=" abv"; }
      if(conf_trend==1 && conf_stage==511)          { res.quality+=10; res.info+=" cok"; }
      // V30.02: M15-triggered FLAT→UP requires M30 in active bullish fly (511/512) to confirm.
      // Without M30 confirm, cap quality below floor (59) so the entry is blocked by G5-WEAK.
      if(triggerTF==1 && !(conf_trend==1 && (conf_stage==511||conf_stage==512)))
         { res.quality = MathMin(res.quality, 59); res.info += " noM30"; }
   }
   // ── FLAT → DN (strongest SELL) ────────────────────────────────
   else if((prev==3 || prev2==3) && cur==2) {
      res.transition = M5_TRANS_FLAT_TO_DN;
      res.direction  = 2;
      res.quality    = q_base_flat;
      res.info = "Gate:[G5] "+tfl+" t:flat_dn";
      if(mid_ref < mid_ref_1)                      { res.quality+=10; res.info+=" mid-"; }
      if(close_ref < mid_ref && diffMid < 0)        { res.quality+=10; res.info+=" blw"; }
      if(conf_trend==2 && conf_stage==521)          { res.quality+=10; res.info+=" cok"; }
      // V30.02: M15-triggered FLAT→DN requires M30 in active bearish fly (521/522) to confirm.
      if(triggerTF==1 && !(conf_trend==2 && (conf_stage==521||conf_stage==522)))
         { res.quality = MathMin(res.quality, 59); res.info += " noM30"; }
   }
   // ── FLAT → SIDEUP (early BUY warning) ────────────────────────
   else if((prev==3 || prev2==3) && cur==5) {
      res.transition = M5_TRANS_WEAK_UP;
      res.direction  = 1;
      res.quality    = 45;
      res.info = "Gate:[G5] "+tfl+" t:flat_sideup";
      if(conf_trend==1 && conf_stage==511)          { res.quality+=20; res.info+=" cok2"; }
   }
   // ── FLAT → SIDEDN (early SELL warning) ───────────────────────
   else if((prev==3 || prev2==3) && cur==4) {
      res.transition = M5_TRANS_WEAK_DN;
      res.direction  = 2;
      res.quality    = 45;
      res.info = "Gate:[G5] "+tfl+" t:flat_sidedn";
      if(conf_trend==2 && conf_stage==521)          { res.quality+=20; res.info+=" cok2"; }
   }
   // ── UP → DN (direct reversal) ─────────────────────────────────
   else if(prev==1 && cur==2) {
      res.transition = M5_TRANS_UP_TO_DN;
      res.direction  = 2;
      res.quality    = q_base_rev;
      res.info = "Gate:[G5] "+tfl+" t:up_dn";
      if(conf_trend==2 && (conf_stage==521||conf_stage==522)) { res.quality+=15; res.info+=" cok"; }
   }
   // ── DN → UP (direct reversal) ─────────────────────────────────
   else if(prev==2 && cur==1) {
      res.transition = M5_TRANS_DN_TO_UP;
      res.direction  = 1;
      res.quality    = q_base_rev;
      res.info = "Gate:[G5] "+tfl+" t:dn_up";
      if(conf_trend==1 && (conf_stage==511||conf_stage==512)) { res.quality+=15; res.info+=" cok"; }
   }
   // ── UP → FLAT (fading) ────────────────────────────────────────
   else if(prev==1 && cur==3) {
      res.transition = M5_TRANS_UP_TO_FLAT;
      res.direction  = 0;
      res.quality    = 0;
      res.info = "Gate:[G5] "+tfl+" t:up_flat";
   }
   // ── DN → FLAT (fading) ────────────────────────────────────────
   else if(prev==2 && cur==3) {
      res.transition = M5_TRANS_DN_TO_FLAT;
      res.direction  = 0;
      res.quality    = 0;
      res.info = "Gate:[G5] "+tfl+" t:dn_flat";
   }
   // ── SQZ BREAKOUT (midline touch continuation) ─────────────────
   // triggerTF was in SQZ (400-499) last bar → now broke into fly expand
   // Triggered by: M30 shrink + M15 sideway + triggerTF squeezing at midline
   // Higher base quality (75) because midline is a HPC level
   else {
      int ref_stg_prev = BB_datas[triggerTF].BBW_stage[LA_1];
      bool ref_was_sqz = (ref_stg_prev >= 400 && ref_stg_prev < 500);
      int  ref_stg_now = BB_datas[triggerTF].BBW_stage[LA];

      if(ref_was_sqz && (ref_stg_now==521||ref_stg_now==522) && (cur==2||cur==4)) {
         res.transition = M5_TRANS_FLAT_TO_DN;
         res.direction  = 2;
         res.quality    = 75;
         res.info = "Gate:[G5] "+tfl+" t:sqz_brk_dn";
         if(conf_trend==2 && conf_stage==521) { res.quality+=10; res.info+=" cok"; }
         // RC39 (v22.48): confirmTF must be in committed bearish fly or bearish shrink — flat mid=3 is noise
         bool sqz_brk_dn_ok = ((conf_stage==521||conf_stage==522)&&(conf_trend==2||conf_trend==4)) ||
                               (conf_stage==523&&(conf_trend==2||conf_trend==4));
         if(!sqz_brk_dn_ok) { res.quality = MathMin(res.quality, 59); res.info += " noM30"; }
      }
      else if(ref_was_sqz && (ref_stg_now==511||ref_stg_now==512) && (cur==1||cur==5)) {
         res.transition = M5_TRANS_FLAT_TO_UP;
         res.direction  = 1;
         res.quality    = 75;
         res.info = "Gate:[G5] "+tfl+" t:sqz_brk_up";
         if(conf_trend==1 && conf_stage==511) { res.quality+=10; res.info+=" cok"; }
         // RC39 (v22.48): confirmTF must be in committed bullish fly or bullish shrink — flat mid=3 is noise
         bool sqz_brk_up_ok = ((conf_stage==511||conf_stage==512)&&(conf_trend==1||conf_trend==5)) ||
                               (conf_stage==513&&(conf_trend==1||conf_trend==5));
         if(!sqz_brk_up_ok) { res.quality = MathMin(res.quality, 59); res.info += " noM30"; }
      }
      else {
         res.info = "Gate:[G5] "+tfl+" t:stable";
      }
   }

   // H4 shrink quality cap: uncertain macro direction → limit conviction (v22.42)
   int H4_stg_dt = BB_datas[4].BBW_stage[LA];
   if((H4_stg_dt==513||H4_stg_dt==523) && res.quality > 85) res.quality = 85;

   // Quality → size
   if     (res.quality >= 90) res.sizeMulti = 1.0;
   else if(res.quality >= 75) res.sizeMulti = 0.75;
   else if(res.quality >= 60) res.sizeMulti = 0.5;
   else if(res.quality >= 45) res.sizeMulti = 0.25;
   else                       res.sizeMulti = 0.0;

   res.info += " q:"+res.quality+" sz:"+DoubleToString(res.sizeMulti,2);
   return res;
}

struct ShrinkDecision {
   int    direction;
   double sizeMulti;
   string info;
   int    triggerTF;   // v22.45: 0=M5, 1=M15, 2=M30 adaptive trigger TF
};

ShrinkDecision GetShrinkDecision(BB_MTF_Data_struct &BB_datas[], double &close_prices[])
{
   ShrinkDecision result;
   result.direction = 0; result.sizeMulti = 0.0; result.info = ""; result.triggerTF = 0;

   bool M5_shrink  = (BB_datas[0].BBW_stage[LA]==513 || BB_datas[0].BBW_stage[LA]==523);
   bool H4_shrink  = (BB_datas[4].BBW_stage[LA]==513 || BB_datas[4].BBW_stage[LA]==523);
   bool H1_shrink  = (BB_datas[3].BBW_stage[LA]==513 || BB_datas[3].BBW_stage[LA]==523);
   bool M30_shrink = (BB_datas[2].BBW_stage[LA]==513 || BB_datas[2].BBW_stage[LA]==523);
   bool M15_shrink = (BB_datas[1].BBW_stage[LA]==513 || BB_datas[1].BBW_stage[LA]==523);

   if(!M5_shrink && !H4_shrink && !H1_shrink && !M30_shrink && !M15_shrink) {
      result.info = "NO_SHRINK"; return result;
   }

   // Shrink depth penalty
   // M5-only shrink (M15+ still flying) = lightest penalty 0.90x
   // H4 shrink counts as 0.5 weight (slow TF, less impactful on entry timing)
   int shrinkCount = (H4_shrink?1:0) + (H1_shrink?1:0)
                   + (M30_shrink?1:0) + (M15_shrink?1:0);
   double depthPenalty;
   if     (shrinkCount >= 3)            depthPenalty = 0.25;
   else if(shrinkCount == 2)            depthPenalty = 0.50;
   else if(shrinkCount == 1)            depthPenalty = 0.75;
   else if(M5_shrink && shrinkCount==0) depthPenalty = 0.90;  // M5 only
   else                                 depthPenalty = 0.75;
   result.info = "cnt:" + shrinkCount
              + (M5_shrink?"+M5":"")
              + " pen:" + depthPenalty;

   // M15 mid TF check — opposing midtrend blocks trade
   int M15_mid = BB_datas[1].BB_diffMid_Trend[LA];
   int M30_mid = BB_datas[2].BB_diffMid_Trend[LA];

   // Check M15 conflict with M30 direction
   // BB_diffMid_Trend: 1=uptrend  2=dntrend  3=sideway  4=sideway-dn  5=sideway-up
   // Only HARD BLOCK when M15 has a CLEAR directional opposition (mid==1 or mid==2)
   // Sideway variants (4, 5) are weak biases — do NOT block; trade proceeds at reduced signal
   //
   // M30 bullish (1 or 5) + M15 CLEARLY bearish (2) → block
   if((M30_mid==1 || M30_mid==5) && M15_mid==2) {
      result.direction = 0; result.sizeMulti = 0.0;
      result.info += "| Gate:[G4-BLOCK] M30up+M15dn"; return result;
   }
   // M30 bearish (2 or 4) + M15 CLEARLY bullish (1) → block
   if((M30_mid==2 || M30_mid==4) && M15_mid==1) {
      result.direction = 0; result.sizeMulti = 0.0;
      result.info += "| Gate:[G4-BLOCK] M30dn+M15up"; return result;
   }
   // NOT blocked (weak bias only — M15 sideway variants):
   // M30 up + M15 mid=4 (sideway-dn) → proceed, M15 slightly weak
   // M30 dn + M15 mid=5 (sideway-up) → proceed, M15 slightly weak

   // ── H1 FULL-FLY OPPOSING CHECK ──────────────────────────────
   // If H1 is in committed fly (not shrink/SQZ) and opposes M30 direction → block.
   // H1 in SQZ is handled by G0c. H1 in shrink is transitioning — don't block.
   // RC35 (v22.46): extend to include flat mid=3 — same principle as RC18 (H4) and RC14 (M30).
   // H1 fly with mid=3 still carries structural directional bias; flat mid is a pause, not reversal.
   // Apr-27 03:10 SELL H1=511/mid=3 -32.41; Apr-07 19:25 BUY H1=521/mid=3 -1.49; 0 wins lost.
   {
      int  H1_mid_s = BB_datas[3].BB_diffMid_Trend[LA];
      int  H1_stg_s = BB_datas[3].BBW_stage[LA];
      bool H1_fly_s = (H1_stg_s==511||H1_stg_s==512||H1_stg_s==521||H1_stg_s==522);
      if(H1_fly_s) {
         bool H1_bear_fly_b = (H1_stg_s==521||H1_stg_s==522)&&(H1_mid_s==2||H1_mid_s==3||H1_mid_s==4);
         bool H1_bull_fly_b = (H1_stg_s==511||H1_stg_s==512)&&(H1_mid_s==1||H1_mid_s==3||H1_mid_s==5);
         if((M30_mid==1||M30_mid==5) && H1_bear_fly_b) {
            result.direction=0; result.sizeMulti=0.0;
            result.info += "| Gate:[G4b-H1OPP] M30up+H1dn:"+H1_mid_s; return result;
         }
         if((M30_mid==2||M30_mid==4) && H1_bull_fly_b) {
            result.direction=0; result.sizeMulti=0.0;
            result.info += "| Gate:[G4b-H1OPP] M30dn+H1up:"+H1_mid_s; return result;
         }
      }
   }

   // ── MIDLINE SQZ LOADING DETECTION ───────────────────────────
   // M30 shrink + M30 sideway + M15 SQZ = price at M30 midline loading zone (V30.02: M15 trigger)
   // Log the state; entry fires when M15 SQZ breaks (next bar)
   bool M15_sqz_now = (BB_datas[1].BBW_stage[LA] >= 400 &&
                       BB_datas[1].BBW_stage[LA] < 500);
   bool M30_sideway_now = (BB_datas[2].BB_diffMid_Trend[LA] >= 3);
   int  M30_mid_trend   = BB_datas[2].BB_diffMid_Trend[LA];

   if(M15_sqz_now && M30_shrink && M30_sideway_now) {
      if(M30_mid_trend == 2 || M30_mid_trend == 4)
         result.info += "| Gate:[G6-LOAD] dir:SELL";
      else if(M30_mid_trend == 1 || M30_mid_trend == 5)
         result.info += "| Gate:[G6-LOAD] dir:BUY";
      else
         result.info += "| Gate:[G6-LOAD] dir:neutral";
   }

   // Adaptive trigger TF: V30.02 — M15 is the base trigger; escalate to M30 if M15 is noisy
   // M15 noisy (SQZ/shrink) + M30 flying → use M30 midtrend as trigger
   int shrinkTriggerTF = 1;  // M15 is always the default trigger TF
   {
      int m15_stg_t = BB_datas[1].BBW_stage[LA];
      int m30_stg_t = BB_datas[2].BBW_stage[LA];
      bool m15_noisy = (m15_stg_t>=400&&m15_stg_t<500)||m15_stg_t==513||m15_stg_t==523;
      bool m30_fly   = m30_stg_t==511||m30_stg_t==512||m30_stg_t==521||m30_stg_t==522;
      if(m15_noisy && m30_fly) shrinkTriggerTF = 2;
   }
   result.triggerTF = shrinkTriggerTF;
   // Get transition using adaptive trigger TF
   M5_TransitionResult trans = DetectM5Transition(BB_datas, close_prices, shrinkTriggerTF);

   // G4k-M15SHRKopp: M30 as trigger (triggerTF==2) + M15 in opposing shrink direction (V30.02)
   // When M30 is the trigger because M15 is noisy, M15 in opposing shrink still blocks.
   // M15=523 (bearish shrink) opposes BUY; M15=513 (bullish shrink) opposes SELL.
   if(shrinkTriggerTF == 2 && trans.direction != 0) {
      int  m15_stg_k     = BB_datas[1].BBW_stage[LA];
      int  m15_mid_k     = BB_datas[1].BB_diffMid_Trend[LA];
      bool m15_opp_buy_k = (m15_stg_k==523)&&(m15_mid_k==2||m15_mid_k==3||m15_mid_k==4);
      bool m15_opp_sel_k = (m15_stg_k==513)&&(m15_mid_k==1||m15_mid_k==3||m15_mid_k==5);
      if((trans.direction==1&&m15_opp_buy_k)||(trans.direction==2&&m15_opp_sel_k)) {
         trans.direction = 0; trans.quality = 0;
         trans.info += " | Gate:[G4k-M15SHRKopp] M15stg:"+IntegerToString(m15_stg_k)+" M15mid:"+IntegerToString(m15_mid_k);
      }
   }
   // G4k-TRIGDIR: trigger TF stage contradicts generated direction (v22.43, RC31)
   // When triggerTF in bullish fly (511/512) but midtrend fires SELL, or bearish fly (521/522) + BUY.
   // RC31: Apr-24 SELL tTF=2 M30=512 bullish fly, midtrend momentarily 3->2 -> -16.01.
   if(trans.direction != 0) {
      int  trig_stg_k = BB_datas[shrinkTriggerTF].BBW_stage[LA];
      bool trig_bull_k = (trig_stg_k==511||trig_stg_k==512);
      bool trig_bear_k = (trig_stg_k==521||trig_stg_k==522);
      if((trans.direction==1&&trig_bear_k)||(trans.direction==2&&trig_bull_k)) {
         trans.direction = 0; trans.quality = 0;
         trans.info += " | Gate:[G4k-TRIGDIR] trigTF:"+IntegerToString(shrinkTriggerTF)+" stg:"+IntegerToString(trig_stg_k);
      }
   }

   result.info += "| " + trans.info;

   // Direction only — lot size fixed at 0.01 externally
   if(trans.direction != 0 && trans.quality >= 60) {
      result.direction = trans.direction;
      result.sizeMulti = 1.0;   // unused; lots always baseLot
      if(StringFind(trans.info,"sqz_brk") >= 0)
         result.info += "| Gate:[G6-ENTRY]";
      else
         result.info += "| Gate:[G5-ENTRY]";
   }
   else if(trans.direction != 0 && trans.quality >= 45) {
      // v22.45: quality floor raised to 60 — G5-EARLY (M15 SQZ exception) removed.
      // Weak transitions (quality 45-59) are blocked regardless of M15 SQZ state.
      result.direction = 0; result.sizeMulti = 0.0;
      result.info += "| Gate:[G5-WEAK]";
   }
   else if(trans.transition==M5_TRANS_UP_TO_FLAT||trans.transition==M5_TRANS_DN_TO_FLAT) {
      result.direction = 0; result.sizeMulti = 0.0;
      result.info += "| Gate:[G5-FADE]";
   }
   else {
      result.direction = 0; result.sizeMulti = 0.0;
      result.info += "| Gate:[G5-NONE]";
   }
   // G4c: M15 opposing check (v22.19 fly, v22.24 shrink, v22.30 SQZ+opposing mid).
   // Block G6-BUY when M15 is in active bearish fly/shrink, block G6-SELL when bullish fly/shrink.
   // v22.24: added 523&&(mid==2||4) and 513&&(mid==1||5) — bearish/bullish shrink with committed mid.
   // v22.30: added SQZ (400-499) + opposing mid — mirrors RC7 (G0b-M15OPP SQZ gap) for shrink path.
   // RC16: Mar-02 G5-EARLY BUY with M15s=415/mid=4 (SQZ bearish) → G4c missed SQZ → -62.63.
   // Cascade path (G0b-M15OPP) already blocked same bar via RC7; shrink path had no equivalent.
   if(result.direction != 0) {
      int  m15_stg_fd = BB_datas[1].BBW_stage[LA];
      int  m15_mid_fd = BB_datas[1].BB_diffMid_Trend[LA];
      bool m15_fly_dn_fd=(m15_stg_fd==521)||(m15_stg_fd==522&&m15_mid_fd!=5)
                        ||(m15_stg_fd==523&&(m15_mid_fd==2||m15_mid_fd==4))
                        ||((m15_stg_fd>=400&&m15_stg_fd<500)&&(m15_mid_fd==2||m15_mid_fd==4));
      bool m15_fly_up_fd=(m15_stg_fd==511)||(m15_stg_fd==512&&m15_mid_fd!=4)
                        ||(m15_stg_fd==513&&(m15_mid_fd==1||m15_mid_fd==5))
                        ||((m15_stg_fd>=400&&m15_stg_fd<500)&&(m15_mid_fd==1||m15_mid_fd==5));
      if(result.direction==1 && m15_fly_dn_fd) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4c-M15OPP] BUY+M15:"+m15_stg_fd+"/"+m15_mid_fd; return result;
      }
      if(result.direction==2 && m15_fly_up_fd) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4c-M15OPP] SELL+M15:"+m15_stg_fd+"/"+m15_mid_fd; return result;
      }
   }
   // G4d: G4-BLOCK gap-fill (v22.22) — G4-BLOCK only fires on M30_mid==1/2 conflicts.
   // M30_mid==3 (flat) + M15 opposing = missed gap. Block only this specific conflict.
   if(result.direction==2 && M30_mid==3 && M15_mid==1) {
      result.direction=0; result.sizeMulti=0.0;
      result.info += "| Gate:[G4d-M30SID] SELL+M30f+M15up:"+M15_mid; return result;
   }
   if(result.direction==1 && M30_mid==3 && M15_mid==2) {
      result.direction=0; result.sizeMulti=0.0;
      result.info += "| Gate:[G4d-M30SID] BUY+M30f+M15dn:"+M15_mid; return result;
   }
   // G4e: H4 macro opposing filter (v22.23, extended v22.32 flat-mid shrink).
   // Block shrink-path entries when H4 is in committed opposing fly or shrink.
   // v22.23: 521/522/523+mid2/4 and 511/512/513+mid1/5.
   // v22.32 extension: 523&&mid==3 and 513&&mid==3 — shrink with flat mid has no reversal
   // signal yet (mirrors RC14/v22.29 for G0b-M30OPP). RC18: Feb-09 G6-BUY H4=523/3 -11.49,
   // Feb-27 G6-SELL H4=513/3 -15.72, Apr-20 G6-SELL H4=513/3 -20.19 +15.13.
   if(result.direction != 0) {
      int  H4_stg_se = BB_datas[4].BBW_stage[LA];
      int  H4_mid_se = BB_datas[4].BB_diffMid_Trend[LA];
      // G4e-H4OPP: only committed fly blocks — shrink (513/523) is a transition zone
      // where H4 reversals are viable (v22.49: removed 513/523 shrink clauses).
      bool H4_fly_dn_se = (H4_stg_se==521||H4_stg_se==522)&&(H4_mid_se==2||H4_mid_se==4);
      bool H4_fly_up_se = (H4_stg_se==511||H4_stg_se==512)&&(H4_mid_se==1||H4_mid_se==5);
      if(result.direction==1 && H4_fly_dn_se) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4e-H4OPP] BUY+H4:"+H4_stg_se+"/"+H4_mid_se; return result;
      }
      if(result.direction==2 && H4_fly_up_se) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4e-H4OPP] SELL+H4:"+H4_stg_se+"/"+H4_mid_se; return result;
      }
   }
   // G4j-D1OPP: D1 opposing macro filter in shrink path, H4-SQZ only (RC24, v22.37).
   // Scope: only when H4 is in SQZ (400-499) — G4e-H4OPP covers fly/shrink stages. When H4
   // is compressed, D1 (the daily TF above H4) serves as the macro backup conviction source.
   // Only blocks committed D1 fly (511/512 or 521/522) — shrink stages are excluded to avoid
   // blocking transitional periods. Confirmed: Jan-16 19:55 G6-SELL H4=423/mid=3 D1=512/mid=1 → -97.03.
   if(result.direction != 0) {
      int H4_stg_d1s = BB_datas[4].BBW_stage[LA];
      if(H4_stg_d1s>=400 && H4_stg_d1s<500) {
         int  D1_stg_sd = BB_datas[5].BBW_stage[LA];
         int  D1_mid_sd = BB_datas[5].BB_diffMid_Trend[LA];
         bool D1_fly_up_sd = (D1_stg_sd==511||D1_stg_sd==512)&&(D1_mid_sd==1||D1_mid_sd==5);
         bool D1_fly_dn_sd = (D1_stg_sd==521||D1_stg_sd==522)&&(D1_mid_sd==2||D1_mid_sd==4);
         if(result.direction==1 && D1_fly_dn_sd) {
            result.direction=0; result.sizeMulti=0.0;
            result.info += "| Gate:[G4j-D1OPP] BUY+D1:"+D1_stg_sd+"/"+D1_mid_sd+"+H4SQZ"; return result;
         }
         if(result.direction==2 && D1_fly_up_sd) {
            result.direction=0; result.sizeMulti=0.0;
            result.info += "| Gate:[G4j-D1OPP] SELL+D1:"+D1_stg_sd+"/"+D1_mid_sd+"+H4SQZ"; return result;
         }
      }
   }
   // G4f: M30 macro opposing filter (v22.26 fly/shrink, v22.27 SQZ+opposing mid).
   // Block G6-BUY when M30 bearish fly/shrink (521/522/523+mid2/4) or SQZ+mid2/4.
   // Block G6-SELL when M30 bullish fly/shrink (511/512/513+mid1/5) or SQZ+mid1/5.
   // v22.26: Feb-24 G6-BUY M30stg=522/mid=2 (bearish fly) → -13.99.
   // v22.27: Feb-03 G6-SELL M30stg=402/mid=2 (SQZ opposing) → -64.72. Mirrors RC7 for shrink path.
   if(result.direction != 0) {
      int  M30_stg_sf = BB_datas[2].BBW_stage[LA];
      int  M30_mid_sf = BB_datas[2].BB_diffMid_Trend[LA];
      bool M30_fly_dn_sf = ((M30_stg_sf==521||M30_stg_sf==522||M30_stg_sf==523)
                          ||(M30_stg_sf>=400&&M30_stg_sf<500))
                         && (M30_mid_sf==2||M30_mid_sf==4);
      bool M30_fly_up_sf = ((M30_stg_sf==511||M30_stg_sf==512||M30_stg_sf==513)
                          ||(M30_stg_sf>=400&&M30_stg_sf<500))
                         && (M30_mid_sf==1||M30_mid_sf==5);
      if(result.direction==1 && M30_fly_dn_sf) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4f-M30OPP] BUY+M30:"+M30_stg_sf+"/"+M30_mid_sf; return result;
      }
      if(result.direction==2 && M30_fly_up_sf) {
         result.direction=0; result.sizeMulti=0.0;
         result.info += "| Gate:[G4f-M30OPP] SELL+M30:"+M30_stg_sf+"/"+M30_mid_sf; return result;
      }
   }
   return result;
}

//+------------------------------------------------------------------+
// Draw gate info label on chart at current bar price
// tag      = gate label e.g. "[G0] dual_sideway"
// price    = chart price level for label anchor
// tf_idx   = which BB_datas TF to use for color/font (default 1=M15)
// Calls the existing DRAW_LABEL function already defined in main EA
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
// Trade CSV Logger — writes one row per closed trade to a CSV file
// File: TofyTrade3_<date>.csv in MQL5/Files folder
// Paste the CSV to Claude for trade-by-trade analysis
//+------------------------------------------------------------------+

string g_csv_filename    = "";
int    g_csv_handle      = INVALID_HANDLE;
string g_last_trade_info = "";
int    g_entry_stages[5];     // BBW_stage[LA] M5..H4 at entry time
int    g_entry_mids[5];       // BB_diffMid_Trend[LA] M5..H4 at entry time
int    g_entry_atrsl_dir = 0; // ATRSL1BUF.dir at entry time

void CSV_Init()
{
   string date = StringSubstr(TimeToString(TimeCurrent(),TIME_DATE),0,10);
   StringReplace(date, ".", "-");
   g_csv_filename = "TofyTrade3_" + date + ".csv";
   g_csv_handle   = FileOpen(g_csv_filename, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   if(g_csv_handle == INVALID_HANDLE) {
      Print("CSV_Init: cannot open file ", g_csv_filename); return;
   }
   FileWrite(g_csv_handle,
      "ticket","type","open_time","close_time",
      "open_price","close_price","lots",
      "profit_usd","profit_pips",
      "gate_labels","sl_at_entry",
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
   if(g_csv_handle != INVALID_HANDLE) {
      FileClose(g_csv_handle);
      g_csv_handle = INVALID_HANDLE;
      Print("CSV saved: ", g_csv_filename);
   }
}

void CSV_LogTrade(int ticket,
                  BB_MTF_Data_struct &BB_datas[],
                  ATRSLBUF_struct    &ATRSL1BUF,
                  string             trade_info)
{
   if(g_csv_handle == INVALID_HANDLE) return;
   if(!OrderSelect(ticket, SELECT_BY_TICKET)) return;

   string type_str = (OrderType()==OP_BUY) ? "BUY" : "SELL";
   double open_p   = OrderOpenPrice();
   double close_p  = OrderClosePrice();
   double profit   = OrderProfit() + OrderSwap() + OrderCommission();
   double pips     = (OrderType()==OP_BUY)
                     ? (close_p - open_p) / _Point
                     : (open_p  - close_p) / _Point;

   string labels = trade_info;
   StringReplace(labels, ",", ";");

   FileWrite(g_csv_handle,
      IntegerToString(ticket), type_str,
      TimeToString(OrderOpenTime(),  TIME_DATE|TIME_SECONDS),
      TimeToString(OrderCloseTime(), TIME_DATE|TIME_SECONDS),
      DoubleToString(open_p,  _Digits),
      DoubleToString(close_p, _Digits),
      DoubleToString(OrderLots(), 2),
      DoubleToString(profit, 2),
      DoubleToString(pips,   1),
      labels, DoubleToString(OrderStopLoss(), _Digits),
      IntegerToString(g_entry_stages[0]),
      IntegerToString(g_entry_stages[1]),
      IntegerToString(g_entry_stages[2]),
      IntegerToString(g_entry_stages[3]),
      IntegerToString(g_entry_stages[4]),
      IntegerToString(g_entry_mids[0]),
      IntegerToString(g_entry_mids[1]),
      IntegerToString(g_entry_mids[2]),
      IntegerToString(g_entry_mids[3]),
      IntegerToString(g_entry_mids[4]),
      IntegerToString(g_entry_atrsl_dir),
      IntegerToString(BB_datas[0].BBW_stage[LA]),
      IntegerToString(BB_datas[1].BBW_stage[LA]),
      IntegerToString(BB_datas[2].BBW_stage[LA]),
      IntegerToString(BB_datas[3].BBW_stage[LA]),
      IntegerToString(BB_datas[4].BBW_stage[LA]),
      IntegerToString(BB_datas[0].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[1].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[2].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[3].BB_diffMid_Trend[LA]),
      IntegerToString(BB_datas[4].BB_diffMid_Trend[LA]),
      IntegerToString(ATRSL1BUF.dir));
}

void CSV_CaptureEntryContext(string trade_info,
                              BB_MTF_Data_struct &BB_datas[],
                              ATRSLBUF_struct    &ATRSL1BUF)
{
   g_last_trade_info = trade_info;
   for(int i = 0; i <= 4; i++) {
      g_entry_stages[i] = (int)BB_datas[i].BBW_stage[LA];
      g_entry_mids[i]   = (int)BB_datas[i].BB_diffMid_Trend[LA];
   }
   g_entry_atrsl_dir = ATRSL1BUF.dir;
}

//+------------------------------------------------------------------+
// Compact Stats Tracker — aggregates per-gate win/loss in memory
// OnDeinit: call Stats_Print() → paste ~25 lines to Claude
//+------------------------------------------------------------------+

#define STATS_GATES 16

string g_stat_labels[STATS_GATES] = {
   "G6-BUY","G6-SELL","G0b-TOUCH-B","G0b-TOUCH-S",
   "G5-ENTRY-B","G5-ENTRY-S","G6-ENTRY-B","G6-ENTRY-S",
   "FLY-BUY","FLY-SELL","PHASE2-BUY","PHASE2-SELL",
   "G0c-SQZLOCK","H4-OPPOSE","G0-HOLD","G7-TOOSOON"
};
int    g_stat_fires[STATS_GATES];
int    g_stat_wins [STATS_GATES];
int    g_stat_loss [STATS_GATES];
double g_stat_pips [STATS_GATES];
int    g_stat_open_gate  = -1;
double g_stat_open_price = 0;

void Stats_Init()
{
   for(int i=0; i<STATS_GATES; i++) {
      g_stat_fires[i]=0; g_stat_wins[i]=0;
      g_stat_loss[i]=0;  g_stat_pips[i]=0.0;
   }
   g_stat_open_gate = -1;
}

void Stats_RecordEntry(string trade_info, int trade_act, double open_price)
{
   g_stat_open_price = open_price;
   g_stat_open_gate  = -1;
   int dir = (trade_act == 1) ? 1 : 2;
   // Shrink path entries (exact label match — highest priority)
   if(StringFind(trade_info,"G6-BUY")    >= 0){ g_stat_open_gate=0; g_stat_fires[0]++; return; }
   if(StringFind(trade_info,"G6-SELL")   >= 0){ g_stat_open_gate=1; g_stat_fires[1]++; return; }
   // Cascade band touch entries
   if(StringFind(trade_info,"G0b-TOUCH") >= 0 && dir==1){ g_stat_open_gate=2; g_stat_fires[2]++; return; }
   if(StringFind(trade_info,"G0b-TOUCH") >= 0 && dir==2){ g_stat_open_gate=3; g_stat_fires[3]++; return; }
   // Shrink transition entries
   if(StringFind(trade_info,"G5-ENTRY")  >= 0 && dir==1){ g_stat_open_gate=4; g_stat_fires[4]++; return; }
   if(StringFind(trade_info,"G5-ENTRY")  >= 0 && dir==2){ g_stat_open_gate=5; g_stat_fires[5]++; return; }
   // Midline SQZ break entries
   if(StringFind(trade_info,"G6-ENTRY")  >= 0 && dir==1){ g_stat_open_gate=6; g_stat_fires[6]++; return; }
   if(StringFind(trade_info,"G6-ENTRY")  >= 0 && dir==2){ g_stat_open_gate=7; g_stat_fires[7]++; return; }
   // Main fly / breakout entries (G1-OK label)
   if(StringFind(trade_info,"G1-OK")     >= 0 && dir==1){ g_stat_open_gate=8;  g_stat_fires[8]++;  return; }
   if(StringFind(trade_info,"G1-OK")     >= 0 && dir==2){ g_stat_open_gate=9;  g_stat_fires[9]++;  return; }
   // Phase 2 confirmed reversal entries
   if(StringFind(trade_info,"PHASE2-BUY") >= 0)          { g_stat_open_gate=10; g_stat_fires[10]++; return; }
   if(StringFind(trade_info,"PHASE2-SELL")>= 0)          { g_stat_open_gate=11; g_stat_fires[11]++; return; }
   // Fallback: Stats_RecordEntry was called but no label matched — log for diagnosis
   Print("[STATS_DEBUG] unmatched entry act=", trade_act, " info=", trade_info);
}

void Stats_RecordClose(double close_price, int trade_type)
{
   if(g_stat_open_gate < 0) return;
   double pips = (trade_type == OP_BUY)
                 ? (close_price - g_stat_open_price) / _Point
                 : (g_stat_open_price - close_price) / _Point;
   g_stat_pips[g_stat_open_gate] += pips;
   if(pips >= 0) g_stat_wins[g_stat_open_gate]++;
   else          g_stat_loss[g_stat_open_gate]++;
   g_stat_open_gate = -1;
}

void Stats_RecordBlock(string label)
{
   int idx = -1;
   if     (StringFind(label,"G0c-SQZLOCK") >= 0) idx=12;
   else if(StringFind(label,"H4-OPPOSE")   >= 0) idx=13;
   else if(StringFind(label,"G0-HOLD")     >= 0) idx=14;
   else if(StringFind(label,"G7-TOOSOON")  >= 0) idx=15;
   if(idx >= 0) g_stat_fires[idx]++;
}

void Stats_Print()
{
   Print("═══════════════════════════════════════════════════");
   Print("  BACKTEST GATE SUMMARY — paste to Claude");
   Print("═══════════════════════════════════════════════════");
   Print(StringFormat("  %-16s %5s %4s %4s %7s %8s %9s",
         "Gate","Fires","Win","Loss","WinRate","AvgPips","TotPips"));
   Print("  ───────────────────────────────────────────────────────");
   int total_trades=0, total_wins=0;
   double total_pips=0;
   for(int i=0; i<STATS_GATES; i++) {
      if(g_stat_fires[i] == 0) continue;
      int    trades = g_stat_wins[i] + g_stat_loss[i];
      double wr     = (trades > 0) ? (g_stat_wins[i]*100.0/trades) : -1;
      double avg    = (trades > 0) ? (g_stat_pips[i]/trades) : 0;
      string wr_str = (wr < 0) ? "block" : StringFormat("%.0f%%", wr);
      string avg_str= (trades > 0) ? StringFormat("%+.1f", avg) : "—";
      if(i < 12) {
         string tot_str = (trades > 0) ? StringFormat("%+.1f", g_stat_pips[i]) : "—";
         Print(StringFormat("  %-16s %5d %4d %4d %7s %8s %9s",
               g_stat_labels[i], g_stat_fires[i],
               g_stat_wins[i], g_stat_loss[i], wr_str, avg_str, tot_str));
         total_trades += trades; total_wins += g_stat_wins[i]; total_pips += g_stat_pips[i];
      } else {
         Print(StringFormat("  %-16s %5d (blocked — no trade opened)",
               g_stat_labels[i], g_stat_fires[i]));
      }
   }
   Print("  ───────────────────────────────────────────────────────");
   double total_wr   = (total_trades>0) ? (total_wins*100.0/total_trades) : 0;
   double avg_pips   = (total_trades>0) ? (total_pips/total_trades) : 0;
   Print(StringFormat("  %-16s %5d %4d %4d %6.0f%% %+8.1f %+9.1f",
         "TOTAL", total_trades, total_wins,
         total_trades-total_wins, total_wr, avg_pips, total_pips));
   Print("═══════════════════════════════════════════════════");
}

void DrawGateLabel(string tag, double price,
                   BB_MTF_Data_struct &BB_datas[],
                   color labelColor,
                   int tf_idx=1)
{
   datetime curtime = iTime(_Symbol, PERIOD_M5, 0);
   DRAW_LABEL(tag, curtime, price,
              labelColor,                  // semantic color per gate type
              BB_datas[tf_idx].BBFontSize,
              BB_datas[tf_idx].BBArrowWidth,
              90,            // vertical text
              ANCHOR_UPPER,  // hangs down from price point
              BB_datas[tf_idx]);
}


// v22.45: Dynamic minimum hold bars by trigger TF depth (suggestion #3)
// M5-triggered entry waits 3 bars; M15→6; M30→12; H1+→18
int DynMinHold(int trigTF) {
   if(trigTF >= 3) return 18;
   if(trigTF == 2) return 12;
   if(trigTF == 1) return  6;
   return MIN_HOLD_BARS;
}

void Trade_Strategy(
   BB_MTF_Data_struct      &BB_datas[],
   ATRSLBUF_struct         &ATRSL1BUF,
   BB_MTF_Impact_struct    &BBTFImpact,
   ENUM_Trade_Act          &Trade_act,   // OUT: 0=hold  1=exit_sell+buy  2=exit_buy+sell  7=exit_all
   string                  &Trade_info,
   double                  &Trade_lots,
   double                  &Trade_sl,
   int                      BUYS,
   int                      SELLS,
   double                  &close_prices[],
   double                   baseLot = 0.01   // fixed 0.01, one trade at a time
)
{
   Trade_act  = 0;
   Trade_info = "";
   Trade_lots = baseLot;   // always 0.01
   Trade_sl   = 0.0;

   static int      s_exitCooldown        = 0;
   static bool     s_lastEntryWasCascade = false;
   static int      s_lastEntryTrigTF     = 0;

   int MAX_TF = 4;
   int MIN_TF = 0;

   // ── Trend prediction label (drawn every bar for chart analysis) ──
   PredictNextTrend(BB_datas);

   // ── GATE 0: M30+M15 dual sideway — CHECK H1 FIRST ─────────────
   // Fix: require H1 also sideways before exit.
   // H1 still trending → M30+M15 sideway = brief noise → hold trade.
   // All three sideways → genuine pause → exit all.
   int H1_mid = BB_datas[3].BB_diffMid_Trend[LA];
   int M30_mid = BB_datas[2].BB_diffMid_Trend[LA];
   int M15_mid = BB_datas[1].BB_diffMid_Trend[LA];

   // check if 
   if(M30_mid >= 3 && M15_mid >= 3) {
      if(H1_mid >= 3) {
         // All three sideways — genuine pause → exit all
         Trade_act  = 7;
         Trade_lots = 0.0;
         s_exitCooldown = POST_EXIT_COOLDOWN;
         Trade_info = "Gate:[G0] TradeAct:"+IntegerToString(Trade_act)+" M30:" + M30_mid + " M15:" + M15_mid + " H1:" + H1_mid;
         DrawGateLabel("[G0]", close_prices[LA], BB_datas, GATE_CLR_EXIT, 2);
         Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
      }
      else {
         // H1 still trending — M30+M15 noise during fly
         // Block new entries but do NOT close existing trade
         Trade_act  = 0;
         Trade_lots = 0.0;
         Trade_info = "Gate:[G0-HOLD] TradeAct:"+IntegerToString(Trade_act)+" M30:" + M30_mid + " M15:" + M15_mid + " H1:" + H1_mid;
         DrawGateLabel("[G0-HOLD]", BB_datas[3].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 3);
         Stats_RecordBlock(Trade_info);
         Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
      }
   }
   // ── H2L / L2H chain detection ─────────────────────────────────
   int H2L_flyUP_TF=-1, H2L_flyDN_TF=-1;
   int H2L_flyStrink_TF=-1, H2L_sideway_TF=-1;
   int L2H_flyUP_TF=-1, L2H_flyDN_TF=-1;
   int L2H_flyStrink_TF=-1, L2H_sideway_TF=-1;

   for(int i=MAX_TF; i>=MIN_TF; i--) {
      int stage=BB_datas[i].BBW_stage[LA];
      int trend=BB_datas[i].BB_diffMid_Trend[LA];
      int t1=BB_datas[i].BB_diffMid_Trend[LA_1];
      int t2=BB_datas[i].BB_diffMid_Trend[LA_2];
      if((stage==511||stage==512)&&trend==1){ if(i==MAX_TF||H2L_flyUP_TF==i+1) H2L_flyUP_TF=i; else H2L_flyUP_TF=-1; }
      if((stage==521||stage==522)&&trend==2){ if(i==MAX_TF||H2L_flyDN_TF==i+1) H2L_flyDN_TF=i; else H2L_flyDN_TF=-1; }
      if(stage==513||stage==523)            { if(i==MAX_TF||H2L_flyStrink_TF==i+1) H2L_flyStrink_TF=i; }
      bool sq=(stage>=400&&stage<500)&&(trend==3||t1==3||t2==3);
      if(sq) { if(i==MAX_TF||H2L_sideway_TF==i+1) H2L_sideway_TF=i; }
   }
   for(int i=MIN_TF; i<=MAX_TF; i++) {
      int stage=BB_datas[i].BBW_stage[LA];
      int trend=BB_datas[i].BB_diffMid_Trend[LA];
      int t1=BB_datas[i].BB_diffMid_Trend[LA_1];
      int t2=BB_datas[i].BB_diffMid_Trend[LA_2];
      if((stage==511||stage==512)&&trend==1){ if(i==MIN_TF||L2H_flyUP_TF==i-1) L2H_flyUP_TF=i; }
      if((stage==521||stage==522)&&trend==2){ if(i==MIN_TF||L2H_flyDN_TF==i-1) L2H_flyDN_TF=i; }
      if(stage==513||stage==523)            { if(i==MIN_TF||L2H_flyStrink_TF==i-1) L2H_flyStrink_TF=i; }
      bool sq=(stage>=400&&stage<500)&&(trend==3||t1==3||t2==3);
      if(sq) { if(i==MIN_TF||L2H_sideway_TF==i-1) L2H_sideway_TF=i; }
   }

   // ── SHRINK PATH ───────────────────────────────────────────────
   // V30.02: use M15 mid (trigger TF) as the sideway reference, not M5
   bool H4_shrink =(BB_datas[4].BBW_stage[LA]==513||BB_datas[4].BBW_stage[LA]==523) && BB_datas[1].BB_diffMid_Trend[LA]>=3;
   bool H1_shrink =(BB_datas[3].BBW_stage[LA]==513||BB_datas[3].BBW_stage[LA]==523) && BB_datas[1].BB_diffMid_Trend[LA]>=3;
   bool M30_shrink=(BB_datas[2].BBW_stage[LA]==513||BB_datas[2].BBW_stage[LA]==523) && BB_datas[1].BB_diffMid_Trend[LA]>=3;
   bool M15_shrink=(BB_datas[1].BBW_stage[LA]==513||BB_datas[1].BBW_stage[LA]==523) && BB_datas[1].BB_diffMid_Trend[LA]>=3;

   if(H4_shrink || H1_shrink || M30_shrink || M15_shrink) {
      ShrinkDecision shrink = GetShrinkDecision(BB_datas, close_prices);
      string shrink_prefix = (StringLen(Trade_info)==0)
         ? "Gate:[G6-SHRINK] TradeAct:"+IntegerToString(Trade_act)+" "
         : Trade_info + "| Gate:[G6-SHRINK] ";
      Trade_info = shrink_prefix + shrink.info;

      if(shrink.direction == 1) {
         Trade_act = 1;
         Trade_sl  = GetATRSLStop(ATRSL1BUF, 1);
         s_lastEntryWasCascade = false;          // v22.45
         s_lastEntryTrigTF     = shrink.triggerTF;
         Trade_info += "| Gate:[G6-BUY] sl:"+DoubleToString(Trade_sl,_Digits);
         DrawGateLabel("[G6-BUY]", BB_datas[2].BB_Mid[LA], BB_datas, GATE_CLR_BUY, 2);
      }
      else if(shrink.direction == 2) {
         Trade_act = 2;
         Trade_sl  = GetATRSLStop(ATRSL1BUF, 2);
         s_lastEntryWasCascade = false;          // v22.45
         s_lastEntryTrigTF     = shrink.triggerTF;
         Trade_info += "| Gate:[G6-SELL] sl:"+DoubleToString(Trade_sl,_Digits);
         DrawGateLabel("[G6-SELL]", BB_datas[2].BB_Mid[LA], BB_datas, GATE_CLR_SELL, 2);
      }
      else {
         // M15 opposing during shrink → exit all (V30.02: M15 is the trigger TF)
         int M15_now_rev = BB_datas[1].BB_diffMid_Trend[LA];
         if((M15_now_rev==2&&BUYS>0)||(M15_now_rev==1&&SELLS>0)) {
            Trade_act=7; Trade_lots=0.0;
            s_exitCooldown=POST_EXIT_COOLDOWN;
            Trade_info += "| Gate:[G6-REV] M15:"+M15_now_rev;
            DrawGateLabel("[G6-REV]", close_prices[LA], BB_datas, GATE_CLR_EXIT, 2);
         }
      }
   }
   else {
      // ── MAIN FLY / BREAKOUT ──────────────────────────────────
      bool htfDN  =(H2L_flyDN_TF!=-1), htfUP=(H2L_flyUP_TF!=-1);
      bool htfShrk=(H2L_flyStrink_TF!=-1), htfSide=(H2L_sideway_TF!=-1);
      bool ltfUP  =(L2H_flyUP_TF!=-1), ltfDN=(L2H_flyDN_TF!=-1);
      int  direction=0;
      int  H1_mid_fly = BB_datas[3].BB_diffMid_Trend[LA];

      if     (ltfUP&&htfDN&&!htfUP)                                                direction=1;  // Case 1 — reversal, H1 opposing expected
      else if(ltfDN&&htfUP&&!htfDN)                                                direction=2;  // Case 2 — reversal, H1 opposing expected
      else if(ltfUP&&L2H_flyUP_TF>=1&&(htfShrk||htfSide)&&!htfDN&&H1_mid_fly!=2) direction=1;  // Case 3 — breakout, H1 must not be clearly dn
      else if(ltfDN&&L2H_flyDN_TF>=1&&(htfShrk||htfSide)&&!htfUP&&H1_mid_fly!=1) direction=2;  // Case 4 — breakout, H1 must not be clearly up
      else if((ltfUP&&L2H_flyUP_TF>=1&&(htfShrk||htfSide)&&!htfDN&&H1_mid_fly==2) ||
              (ltfDN&&L2H_flyDN_TF>=1&&(htfShrk||htfSide)&&!htfUP&&H1_mid_fly==1)) {
         Trade_info = "Gate:[G7-H1OPP] TradeAct:"+IntegerToString(Trade_act)+" H1:"+H1_mid_fly;
         DrawGateLabel("[G7-H1OPP]", BB_datas[3].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 3);
         Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
      }
      else if((ltfUP||ltfDN)&&(htfShrk||htfSide))                                 { /* no chain — direction stays 0 */ }

      if(direction != 0) {
         // ── H4 SOFT BIAS FILTER ──────────────────────────────────────
         // H4 flying clearly OPPOSITE to intended direction → skip trade
         // Avoids counter-macro-trend entries (seen as churn in backtest)
         // H4 SQZ or sideway → neutral, allow trade through
         // Cascade (G0b) trades exempt — mean-reversion bounces are valid
         int H4_mid_bias   = BB_datas[4].BB_diffMid_Trend[LA];
         int H4_stage_bias = BB_datas[4].BBW_stage[LA];
         bool H4_fly_up  = (H4_stage_bias==511||H4_stage_bias==512)
                        && (H4_mid_bias==1||H4_mid_bias==5);
         bool H4_fly_dn  = (H4_stage_bias==521||H4_stage_bias==522)
                        && (H4_mid_bias==2||H4_mid_bias==4);
         bool H4_in_sqz  = (H4_stage_bias>=400 && H4_stage_bias<500);

         if(direction==1 && H4_fly_dn) {
            // BUY signal but H4 clearly bearish fly → skip
            Trade_info = "Gate:[H4-OPPOSE] TradeAct:"+IntegerToString(Trade_act)+" H4_dn:"+H4_mid_bias;
            Stats_RecordBlock(Trade_info);
            DrawGateLabel("[H4-OPPOSE]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_H4, 4);
            direction = 0;
         }
         else if(direction==2 && H4_fly_up) {
            // SELL signal but H4 clearly bullish fly → skip
            Trade_info = "Gate:[H4-OPPOSE] TradeAct:"+IntegerToString(Trade_act)+" H4_up:"+H4_mid_bias;
            Stats_RecordBlock(Trade_info);
            DrawGateLabel("[H4-OPPOSE]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_H4, 4);
            direction = 0;
         }
         else if(H4_in_sqz) {
            // H4 compressed — macro direction unclear.
            // V30.02: require M15 diffMidTrend to confirm direction (M15 is the trigger TF).
            int M15_mid_sqz = BB_datas[1].BB_diffMid_Trend[LA];
            bool M15_confirms = (direction==1 && (M15_mid_sqz==1||M15_mid_sqz==5))
                             || (direction==2 && (M15_mid_sqz==2||M15_mid_sqz==4));
            Trade_info = "Gate:[H4-SQZ] TradeAct:"+IntegerToString(Trade_act)
                       + " M15mid:"+M15_mid_sqz;
            DrawGateLabel("[H4-SQZ]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_H4, 4);
            if(!M15_confirms) { direction = 0; }
            else {
               // G4g-H1H4SQZ: H4 SQZ + H1 also SQZ = both macro TFs compressed (RC17, v22.32).
               // When H1 and H4 are simultaneously in SQZ, the macro is doubly uncertain.
               // LTF fly signals are unreliable range noise. M5 confirmation is insufficient
               // when H1 provides zero macro conviction. 5 losses -112.56, 1 win +1.62.
               // Confirmed: Jan-16 three SELL losses (H4=423/3+H1=423/4), Apr-21 BUY -39.79.
               bool H1_also_sqz = (BB_datas[3].BBW_stage[LA]>=400 && BB_datas[3].BBW_stage[LA]<500);
               if(H1_also_sqz) {
                  direction = 0;
                  Trade_info += "| Gate:[G4g-H1H4SQZ] H1stg:"+IntegerToString(BB_datas[3].BBW_stage[LA]);
                  DrawGateLabel("[G4g-H1H4SQZ]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 4);
               }
               // G4h-H4M30SQZ: H4 SQZ + M30 also SQZ = macro+mid TF both compressed (RC20b, v22.34).
               // When M30 is also compressed alongside H4-SQZ, the mid-timeframe primary trend driver
               // provides no direction. H1/M15/M5 fly is noise within double-compressed macro+mid context.
               // Confirmed: Apr-13 14:50 SELL H4=423/mid=2 M30=423/mid=3 → -21.13; Mar-26 09:00 → -19.13.
               if(direction != 0) {
                  bool M30_also_sqz = (BB_datas[2].BBW_stage[LA]>=400 && BB_datas[2].BBW_stage[LA]<500);
                  if(M30_also_sqz) {
                     direction = 0;
                     Trade_info += "| Gate:[G4h-H4M30SQZ] M30stg:"+IntegerToString(BB_datas[2].BBW_stage[LA]);
                     DrawGateLabel("[G4h-H4M30SQZ]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 4);
                  }
               }
               // G4i-H4M30FLY: H4-SQZ + M30 opposing fly in main fly path (RC21, v22.35).
               // When H4 is compressed (no macro conviction), M30 becomes the highest reliable TF.
               // M30 in committed opposing fly (511/512 opposing SELL, 521/522 opposing BUY)
               // provides clear macro contradiction. Mirrors H4-OPPOSE logic for the H4-SQZ path.
               // Confirmed: Jan-15 16:00 SELL H4=423/mid=3, M30=511/mid=3 → -26.73.
               if(direction != 0) {
                  int M30_stg_i = BB_datas[2].BBW_stage[LA];
                  int M30_mid_i = BB_datas[2].BB_diffMid_Trend[LA];
                  bool M30_opp_sell = (M30_stg_i==511||M30_stg_i==512)&&(M30_mid_i==1||M30_mid_i==3||M30_mid_i==5);
                  bool M30_opp_buy  = (M30_stg_i==521||M30_stg_i==522)&&(M30_mid_i==2||M30_mid_i==3||M30_mid_i==4);
                  if((direction==2&&M30_opp_sell)||(direction==1&&M30_opp_buy)) {
                     direction = 0;
                     Trade_info += "| Gate:[G4i-H4M30FLY] M30stg:"+IntegerToString(M30_stg_i)+" M30mid:"+IntegerToString(M30_mid_i);
                     DrawGateLabel("[G4i-H4M30FLY]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 4);
                  }
               }
               // G4j-D1OPP in main fly H4-SQZ path (RC24, v22.37). H4 compressed = no macro conviction;
               // D1 fly is the next reliable macro reference. Only committed D1 fly (511/512 or 521/522),
               // no shrink — conservative to avoid blocking D1 trend transitions.
               // Confirmed: Jan-30 12:00 SELL H4=403/mid=3 D1=512/mid=1 → -52.19 (G0e-MAXLOSS cap);
               // Jan-30 15:45 SELL H4=403/mid=3 D1=512/mid=1 → -71.83 (G0e-MAXLOSS gap).
               if(direction != 0) {
                  int D1_stg_j = BB_datas[5].BBW_stage[LA];
                  int D1_mid_j = BB_datas[5].BB_diffMid_Trend[LA];
                  bool D1_fly_up_j = (D1_stg_j==511||D1_stg_j==512)&&(D1_mid_j==1||D1_mid_j==5);
                  bool D1_fly_dn_j = (D1_stg_j==521||D1_stg_j==522)&&(D1_mid_j==2||D1_mid_j==4);
                  if((direction==1&&D1_fly_dn_j)||(direction==2&&D1_fly_up_j)) {
                     direction = 0;
                     Trade_info += "| Gate:[G4j-D1OPP] D1stg:"+IntegerToString(D1_stg_j)+" D1mid:"+IntegerToString(D1_mid_j);
                     DrawGateLabel("[G4j-D1OPP]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 4);
                  }
               }
            }
         }
      }

      if(direction != 0) {
         // ── NORMAL FLY: use M30 + M15 midtrend for trend, NOT ATRSL ──
         // During fly (511/512/521/522) M5 may briefly squeeze (noise).
         // M15 may also show short squeezes. ATRSL lags during these.
         // Use M30 midtrend as primary trend reference, M15 as secondary.
         // ATRSL is kept for STOP PLACEMENT only (not trend gating).

         int M30_mid_fly = BB_datas[2].BB_diffMid_Trend[LA];
         int M15_mid_fly = BB_datas[1].BB_diffMid_Trend[LA];

         // Trend confirmation: M30 OR M15 must agree with direction
         bool mid_confirms =
            (direction==1 && (M30_mid_fly==1||M30_mid_fly==5||
                              M15_mid_fly==1||M15_mid_fly==5)) ||
            (direction==2 && (M30_mid_fly==2||M30_mid_fly==4||
                              M15_mid_fly==2||M15_mid_fly==4));

         if(!mid_confirms) {
            // Neither M30 nor M15 midtrend confirms — sideway/noise, skip
            string g1f_seg = "Gate:[G1-FAIL] M30:"+M30_mid_fly+" M15:"+M15_mid_fly;
            Trade_info = (StringLen(Trade_info)==0) ? g1f_seg+" TradeAct:"+IntegerToString(Trade_act) : Trade_info+"| "+g1f_seg;
            DrawGateLabel("[G1-FAIL]", BB_datas[0].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 2);
            direction=0;
         } else {
            string g1ok_seg = "Gate:[G1-OK] M30:"+M30_mid_fly+" M15:"+M15_mid_fly;
            Trade_info = (StringLen(Trade_info)==0) ? g1ok_seg+" TradeAct:"+IntegerToString(Trade_act) : Trade_info+"| "+g1ok_seg;
         }
      }

      if(direction != 0) {
         // Gate 4: M15 hard conflict — only clear directional opposition
         // Sideway variants (4,5) are weak bias — not blocked
         int M15_mid_now = BB_datas[1].BB_diffMid_Trend[LA];
         if((direction==1 && M15_mid_now==2) ||
            (direction==2 && M15_mid_now==1)) {
            Trade_info += "| Gate:[G4-BLOCK] M15:"+BB_datas[1].BB_diffMid_Trend[LA];
            direction=0;
         }
      }

      // ── M15 ENTRY TRIGGER (V30.02) ───────────────────────────────
      // M15 BBdiffMidTrend transition is the entry signal for the fly path.
      // M5 removed as trigger due to noise; M30 is the confirmTF for quality boosts.
      if(direction != 0) {
         M5_TransitionResult trans = DetectM5Transition(BB_datas, close_prices, 1);
         Trade_info += "| " + trans.info;
         if(trans.direction == direction && trans.quality >= 60) {
            Trade_act  = (ENUM_Trade_Act)trans.direction;
            Trade_sl   = GetATRSLStop(ATRSL1BUF, trans.direction);
            s_lastEntryTrigTF     = 1;
            s_lastEntryWasCascade = false;
            Trade_info += "| Gate:[FLY-" + (trans.direction==1 ? "BUY" : "SELL") + "] sl:" + DoubleToString(Trade_sl, _Digits);
            DrawGateLabel(trans.direction==1 ? "[FLY-BUY]" : "[FLY-SELL]",
                          BB_datas[1].BB_Mid[LA], BB_datas,
                          trans.direction==1 ? GATE_CLR_BUY : GATE_CLR_SELL, 1);
         } else if(trans.transition==M5_TRANS_UP_TO_FLAT || trans.transition==M5_TRANS_DN_TO_FLAT) {
            Trade_act  = 7; Trade_lots = 0.0;
            s_exitCooldown = POST_EXIT_COOLDOWN;
            Trade_info += "| Gate:[G5-FADE]";
            DrawGateLabel("[G5-FADE]", close_prices[LA], BB_datas, GATE_CLR_EXIT, 1);
         }
      }
   }
   Print("[TRADEINFO] "+Trade_info+"|act:"+Trade_act+" atrsl:"+ATRSL1BUF.dir);
}