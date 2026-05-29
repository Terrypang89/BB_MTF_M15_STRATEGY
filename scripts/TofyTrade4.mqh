#property copyright "Copyright 2024, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "22.49"
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
      // v22.45: M5-triggered FLAT→UP requires M15 in active bullish fly (511/512) to confirm.
      // Without M15 confirm, cap quality below floor (59) so the entry is blocked by G5-WEAK.
      if(triggerTF==0 && !(conf_trend==1 && (conf_stage==511||conf_stage==512)))
         { res.quality = MathMin(res.quality, 59); res.info += " noM15"; }
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
      // v22.45: M5-triggered FLAT→DN requires M15 in active bearish fly (521/522) to confirm.
      if(triggerTF==0 && !(conf_trend==2 && (conf_stage==521||conf_stage==522)))
         { res.quality = MathMin(res.quality, 59); res.info += " noM15"; }
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
         if(!sqz_brk_dn_ok) { res.quality = MathMin(res.quality, 59); res.info += " noM15"; }
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
         if(!sqz_brk_up_ok) { res.quality = MathMin(res.quality, 59); res.info += " noM15"; }
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
   // M30 shrink + M15 sideway + M5 SQZ = price at M30 midline loading zone
   // Log the state; entry fires when M5 SQZ breaks (next bar)
   bool M5_sqz_now = (BB_datas[0].BBW_stage[LA] >= 400 &&
                      BB_datas[0].BBW_stage[LA] < 500);
   bool M15_sideway_now = (BB_datas[1].BB_diffMid_Trend[LA] >= 3);
   int  M30_mid_trend   = BB_datas[2].BB_diffMid_Trend[LA];

   if(M5_sqz_now && M30_shrink && M15_sideway_now) {
      if(M30_mid_trend == 2 || M30_mid_trend == 4)
         result.info += "| Gate:[G6-LOAD] dir:SELL";
      else if(M30_mid_trend == 1 || M30_mid_trend == 5)
         result.info += "| Gate:[G6-LOAD] dir:BUY";
      else
         result.info += "| Gate:[G6-LOAD] dir:neutral";
   }

   // Adaptive trigger TF: use highest flying TF when lower TFs are noisy (v22.42)
   // M5 noisy (SQZ/shrink) + M15 flying → use M15 midtrend as trigger
   // M5+M15 both noisy + M30 flying → use M30 midtrend as trigger
   int shrinkTriggerTF = 0;
   {
      int m5_stg_t  = BB_datas[0].BBW_stage[LA];
      int m15_stg_t = BB_datas[1].BBW_stage[LA];
      int m30_stg_t = BB_datas[2].BBW_stage[LA];
      bool m5_noisy  = (m5_stg_t>=400&&m5_stg_t<500)||m5_stg_t==513||m5_stg_t==523;
      bool m15_noisy = (m15_stg_t>=400&&m15_stg_t<500)||m15_stg_t==513||m15_stg_t==523;
      bool m15_fly   = m15_stg_t==511||m15_stg_t==512||m15_stg_t==521||m15_stg_t==522;
      bool m30_fly   = m30_stg_t==511||m30_stg_t==512||m30_stg_t==521||m30_stg_t==522;
      if(m5_noisy && m15_fly)                    shrinkTriggerTF = 1;
      else if(m5_noisy && m15_noisy && m30_fly)  shrinkTriggerTF = 2;
   }
   result.triggerTF = shrinkTriggerTF;  // v22.45: export for dynamic hold bars
   // Get transition using adaptive trigger TF
   M5_TransitionResult trans = DetectM5Transition(BB_datas, close_prices, shrinkTriggerTF);

   // G4k-M5SHRKopp: adaptive trigger (triggerTF>0) + M5 in opposing shrink direction (v22.43, RC30)
   // M5=523 (bearish shrink) opposes BUY; M5=513 (bullish shrink) opposes SELL.
   // Blocks even mid=3 (neutral) — unlike G0b-M5OPP which only covers mid=2/4 in cascade path.
   // RC30: Mar-04 BUY M5=523/mid=3 lost -59.24 via M15 adaptive trigger.
   if(shrinkTriggerTF > 0 && trans.direction != 0) {
      int  m5_stg_k       = BB_datas[0].BBW_stage[LA];
      int  m5_mid_k       = BB_datas[0].BB_diffMid_Trend[LA];
      bool m5_opp_buy_k   = (m5_stg_k==523)&&(m5_mid_k==2||m5_mid_k==3||m5_mid_k==4);
      bool m5_opp_sel_k   = (m5_stg_k==513)&&(m5_mid_k==1||m5_mid_k==3||m5_mid_k==5);
      if((trans.direction==1&&m5_opp_buy_k)||(trans.direction==2&&m5_opp_sel_k)) {
         trans.direction = 0; trans.quality = 0;
         trans.info += " | Gate:[G4k-M5SHRKopp] M5stg:"+IntegerToString(m5_stg_k)+" M5mid:"+IntegerToString(m5_mid_k);
      }
   }
   // G4k-TRIGDIR: adaptive trigger TF stage contradicts generated direction (v22.43, RC31)
   // When triggerTF in bullish fly (511/512) but midtrend fires SELL, or bearish fly (521/522) + BUY.
   // RC31: Apr-24 SELL tTF=2 M30=512 bullish fly, midtrend momentarily 3->2 -> -16.01.
   if(shrinkTriggerTF > 0 && trans.direction != 0) {
      int  trig_stg_k = BB_datas[shrinkTriggerTF].BBW_stage[LA];
      bool trig_bull_k = (trig_stg_k==511||trig_stg_k==512);
      bool trig_bear_k = (trig_stg_k==521||trig_stg_k==522);
      if((trans.direction==1&&trig_bear_k)||(trans.direction==2&&trig_bull_k)) {
         trans.direction = 0; trans.quality = 0;
         trans.info += " | Gate:[G4k-TRIGDIR] trigTF:"+IntegerToString(shrinkTriggerTF)+" stg:"+IntegerToString(trig_stg_k);
      }
   }
   // G4k-M5STG: M5 as trigger (tTF=0) but M5 structural stage contradicts direction (v22.44, RC32)
   // 513 (bullish shrink) + SELL: M5 structural bias is bullish, momentary mid=2 flip is noise.
   // 523 (bearish shrink) + BUY + mid∈{2,3,4}: mid hasn't reversed yet, structural bias still bearish.
   // RC32: Feb-02 23:25 SELL M5=513/mid=2 tTF=0 lost -64.72.
   if(shrinkTriggerTF == 0 && trans.direction != 0) {
      int  m5_stg_s  = BB_datas[0].BBW_stage[LA];
      int  m5_mid_s  = BB_datas[0].BB_diffMid_Trend[LA];
      bool stg_opp_buy  = (m5_stg_s==523)&&(m5_mid_s==2||m5_mid_s==3||m5_mid_s==4);
      bool stg_opp_sell = (m5_stg_s==513);
      if((trans.direction==1&&stg_opp_buy)||(trans.direction==2&&stg_opp_sell)) {
         trans.direction = 0; trans.quality = 0;
         trans.info += " | Gate:[G4k-M5STG] M5stg:"+IntegerToString(m5_stg_s)+" M5mid:"+IntegerToString(m5_mid_s);
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
#define GATE_CLR_AQUA   clrAqua         // G5 flat→up                       — M5 bullish
#define GATE_CLR_ORANGE clrOrange       // G5 flat→dn                       — M5 bearish
#define GATE_CLR_H4     clrDarkOrange   // H4 oppose / H4 SQZ               — macro filter

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
   static bool     s_pendingBuy          = false;
   static bool     s_pendingSell         = false;
   static datetime s_pendingTime         = 0;
   static datetime s_lastEntryTime       = 0;
   static bool     s_lastEntryWasCascade = false;  // v22.45: track if last entry was cascade
   static int      s_lastEntryTrigTF     = 0;      // v22.45: trigger TF of last entry (0=M5,1=M15,2=M30,3=H1)

   int MAX_TF = 4;
   int MIN_TF = 0;

   // ── FIX E: POST-EXIT COOLDOWN ─────────────────────────────────
   if(s_exitCooldown > 0) {
      s_exitCooldown--;
      Trade_info = "Gate:[G0d-COOL] TradeAct:"+IntegerToString(Trade_act)+" cd:" + s_exitCooldown;
      DrawGateLabel("[G0d-COOL]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
      Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
   }

   // ── G0e-MAXLOSS: Emergency exit on deep floating loss (RC4/RC9, v22.36) ──
   if((BUYS > 0 || SELLS > 0) && PositionSelect(_Symbol)) {
      double floatProfit = PositionGetDouble(POSITION_PROFIT);
      if(floatProfit < -MAX_FLOATING_LOSS_USD) {
         s_exitCooldown = POST_EXIT_COOLDOWN;
         Trade_act  = 7;
         Trade_info = "Gate:[G0e-MAXLOSS] profit:" + DoubleToString(floatProfit, 2);
         DrawGateLabel("[G0e-MAXLOSS]", close_prices[LA], BB_datas, GATE_CLR_EXIT, 0);
         Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
      }
   }

   // ── G8-BNDTGT: Cascading sideway band target exit (v22.39, fix v22.40) ─────
   // True cascade: all TFs BELOW the fly TF must be compressed (SQZ/shrink),
   // confirming the fly TF is genuinely the lowest still-flying TF.
   // Also requires ≥1 TF ABOVE compressed to confirm cascade pattern is active.
   if(BUYS > 0 || SELLS > 0) {
      int bndtgt_tf  = -1;
      int bndtgt_dir = 0;
      for(int fi = 1; fi <= MAX_TF && bndtgt_tf < 0; fi++) {
         int  fstg    = BB_datas[fi].BBW_stage[LA];
         bool bullFly = (fstg==511 || fstg==512);
         bool bearFly = (fstg==521 || fstg==522);
         int  updn    = BB_datas[fi].BBUpDn_state[LA];
         if((BUYS > 0 && bullFly && updn == 1) || (SELLS > 0 && bearFly && updn == 2)) {
            bool lower_all_compressed = true;
            for(int fl = 0; fl < fi; fl++) {
               int sl = BB_datas[fl].BBW_stage[LA];
               if(!((sl >= 400 && sl < 500) || sl == 513 || sl == 523)) {
                  lower_all_compressed = false; break;
               }
            }
            if(!lower_all_compressed) continue;
            for(int fi2 = fi+1; fi2 <= MAX_TF; fi2++) {
               int s2 = BB_datas[fi2].BBW_stage[LA];
               if((s2 >= 400 && s2 < 500) || s2 == 513 || s2 == 523) {
                  bndtgt_tf  = fi;
                  bndtgt_dir = (BUYS > 0) ? 1 : 2;
                  break;
               }
            }
         }
      }
      if(bndtgt_tf >= 0) {
         s_exitCooldown = POST_EXIT_COOLDOWN;
         Trade_act  = 7;
         Trade_lots = 0.0;
         string b_touch = (bndtgt_dir == 1) ? "upper" : "lower";
         Trade_info = "Gate:[G8-BNDTGT] TradeAct:7 TF:"+bndtgt_tf+" "+b_touch+"_touch";
         DrawGateLabel("[G8-BNDTGT]", BB_datas[bndtgt_tf].BB_Mid[LA], BB_datas, GATE_CLR_EXIT, bndtgt_tf);
         Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
      }
   }

   // ── FIX A PHASE 2: pending reversal re-evaluation ─────────────
   if(s_pendingBuy || s_pendingSell) {
      int barsSincePending = (s_pendingTime == 0) ? 999 :
         (int)((iTime(_Symbol,PERIOD_M5,0) - s_pendingTime) / PeriodSeconds(PERIOD_M5));
      if(barsSincePending < MIN_HOLD_BARS) {
         Trade_info = "Gate:[PHASE2-WAIT] TradeAct:"+IntegerToString(Trade_act)+" bars:" + barsSincePending + "/" + MIN_HOLD_BARS;
         DrawGateLabel("[PHASE2-WAIT]", close_prices[LA], BB_datas, GATE_CLR_WAIT, 0);
         Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
      }
      int M5c  = BB_datas[0].BB_diffMid_Trend[LA];
      int M15c = BB_datas[1].BB_diffMid_Trend[LA];
      int M30c = BB_datas[2].BB_diffMid_Trend[LA];
      int H1c  = BB_datas[3].BB_diffMid_Trend[LA];
      bool cancelG0  = (M30c >= 3 && M15c >= 3 && H1c >= 3);
      bool H1sqzP    = (BB_datas[3].BBW_stage[LA] >= 400 && BB_datas[3].BBW_stage[LA] < 500);
      bool M30cmpP   = (BB_datas[2].BBW_stage[LA] >= 400 && BB_datas[2].BBW_stage[LA] < 500)
                    || (BB_datas[2].BBW_stage[LA] == 513 || BB_datas[2].BBW_stage[LA] == 523);
      bool M15sqzP   = (BB_datas[1].BBW_stage[LA] >= 400 && BB_datas[1].BBW_stage[LA] < 500);
      bool cancel    = cancelG0 || (H1sqzP && (M30cmpP || M15sqzP));
      if(s_pendingBuy) {
         bool still = (!cancel && (M5c == 1 || M5c == 5 || M15c == 1));
         if(still) {
            Trade_act = 1; Trade_lots = baseLot;
            Trade_sl  = GetATRSLStop(ATRSL1BUF, 1);
            s_lastEntryTime = iTime(_Symbol, PERIOD_M5, 0);
            Trade_info = "Gate:[PHASE2-BUY] TradeAct:"+IntegerToString(Trade_act)+" bars:" + barsSincePending + " sl:" + DoubleToString(Trade_sl,_Digits);
            DrawGateLabel("[PHASE2-BUY]", close_prices[LA], BB_datas, GATE_CLR_BUY, 0);
         } else {
            Trade_info = "Gate:[PHASE2-CANCEL] TradeAct:"+IntegerToString(Trade_act)+" reason:buy_gone";
            DrawGateLabel("[PHASE2-CANCEL]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
         }
         s_pendingBuy = false;
      } else {
         bool still = (!cancel && (M5c == 2 || M5c == 4 || M15c == 2));
         if(still) {
            Trade_act = 2; Trade_lots = baseLot;
            Trade_sl  = GetATRSLStop(ATRSL1BUF, 2);
            s_lastEntryTime = iTime(_Symbol, PERIOD_M5, 0);
            Trade_info = "Gate:[PHASE2-SELL] TradeAct:"+IntegerToString(Trade_act)+" bars:" + barsSincePending + " sl:" + DoubleToString(Trade_sl,_Digits);
            DrawGateLabel("[PHASE2-SELL]", close_prices[LA], BB_datas, GATE_CLR_SELL, 0);
         } else {
            Trade_info = "Gate:[PHASE2-CANCEL] TradeAct:"+IntegerToString(Trade_act)+" reason:sell_gone";
            DrawGateLabel("[PHASE2-CANCEL]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
         }
         s_pendingSell = false;
      }
      Print("[TRADEINFO] " + Trade_info + "|act:" + Trade_act + " atrsl:" + ATRSL1BUF.dir); return;
   }

   // ── GATE 0: M30+M15 dual sideway — CHECK H1 FIRST ─────────────
   // Fix: require H1 also sideways before exit.
   // H1 still trending → M30+M15 sideway = brief noise → hold trade.
   // All three sideways → genuine pause → exit all.
   int M30_mid = BB_datas[2].BB_diffMid_Trend[LA];
   int M15_mid = BB_datas[1].BB_diffMid_Trend[LA];
   int H1_mid  = BB_datas[3].BB_diffMid_Trend[LA];

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

   // ── GATE 0b: CASCADE BAND TOUCH ───────────────────────────────
   {
      int cas_sqzCount = 0, cas_shrinkTF = -1;
      for(int ci = 0; ci <= MAX_TF; ci++) {
         int cstg = BB_datas[ci].BBW_stage[LA];
         if(cstg >= 400 && cstg < 500)        cas_sqzCount++;
         else if(cstg==513 || cstg==523)      cas_shrinkTF = ci;
      }

      if(cas_shrinkTF >= 0 && cas_sqzCount >= 1) {
         // Pink zone: M15+M30 both SQZ → exit all
         bool cas_M15sqz=(BB_datas[1].BBW_stage[LA]>=400&&BB_datas[1].BBW_stage[LA]<500);
         bool cas_M30sqz=(BB_datas[2].BBW_stage[LA]>=400&&BB_datas[2].BBW_stage[LA]<500);
         if(cas_M15sqz && cas_M30sqz) {
            Trade_act=7; Trade_lots=0.0;
            s_exitCooldown=POST_EXIT_COOLDOWN;
            Trade_info="Gate:[G0b-PINK] TradeAct:"+IntegerToString(Trade_act)+" M30+M15_SQZ";
            DrawGateLabel("[G0b-PINK]", close_prices[LA], BB_datas, GATE_CLR_PINK, 1);
            Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
         }

         // Band touch on highest shrink TF
         int htf=cas_shrinkTF;
         int htf_updn=BB_datas[htf].BBUpDn_state[LA];
         double htf_dM =BB_datas[htf].BB_diffMid[LA];
         double htf_dM1=BB_datas[htf].BB_diffMid[LA_1];
         int    htf_mid=BB_datas[htf].BB_diffMid_Trend[LA];

         int cas_dir=0; string cas_touch="";
         if     (htf_updn==2){ cas_dir=1; cas_touch="lower_band"; }
         else if(htf_updn==1){ cas_dir=2; cas_touch="upper_band"; }
         if(cas_dir==0) {
            if(htf_mid==2 && htf_dM1>0 && htf_dM<=0){ cas_dir=2; cas_touch="mid_cross_dn"; }
            else if(htf_mid==1 && htf_dM1<0 && htf_dM>=0){ cas_dir=1; cas_touch="mid_cross_up"; }
         }

         if(cas_dir != 0) {
            // ATRSL direction gate (v22.20: unconditional — was M5-fly-only guard).
            // In cascade context M5 is usually SQZ/shrink so old guard rarely fired;
            // BUY at lower band with ATRSL downtrend and SELL at upper with uptrend
            // reliably lose → return immediately instead of falling through.
            if(cas_dir==1 && ATRSL1BUF.dir==1) {
               Trade_info = "Gate:[G0b-ATRSL] TradeAct:"+IntegerToString(Trade_act)+" reason:ATRSL_dn dir:BUY";
               DrawGateLabel("[G0b-ATRSL]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 1);
               Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
            }
            if(cas_dir==2 && ATRSL1BUF.dir==0) {
               Trade_info = "Gate:[G0b-ATRSL] TradeAct:"+IntegerToString(Trade_act)+" reason:ATRSL_up dir:SELL";
               DrawGateLabel("[G0b-ATRSL]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 1);
               Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
            }
            // M15 opposing filter (v22.19 fly, v22.24 shrink, v22.25 SQZ+opposing mid).
            // v22.25: added SQZ (400-499) with opposing midtrend — blocked Apr-13 BUY M15s=424 mid=2 (-117).
            int  m15_stg_gb = BB_datas[1].BBW_stage[LA];
            int  m15_mid_gb = BB_datas[1].BB_diffMid_Trend[LA];
            bool m15_fly_dn_gb=(m15_stg_gb==521)||(m15_stg_gb==522&&m15_mid_gb!=5)
                              ||(m15_stg_gb==523&&(m15_mid_gb==2||m15_mid_gb==4))
                              ||((m15_stg_gb>=400&&m15_stg_gb<500)&&(m15_mid_gb==2||m15_mid_gb==4));
            bool m15_fly_up_gb=(m15_stg_gb==511)||(m15_stg_gb==512&&m15_mid_gb!=4)
                              ||(m15_stg_gb==513&&(m15_mid_gb==1||m15_mid_gb==5))
                              ||((m15_stg_gb>=400&&m15_stg_gb<500)&&(m15_mid_gb==1||m15_mid_gb==5));
            if((cas_dir==1&&m15_fly_dn_gb)||(cas_dir==2&&m15_fly_up_gb)) {
               Trade_info = "Gate:[G0b-M15OPP] TradeAct:"+IntegerToString(Trade_act)+" M15stg:"+m15_stg_gb+" M15mid:"+m15_mid_gb;
               DrawGateLabel("[G0b-M15OPP]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 1);
               Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
            }
            // H4 fly opposing filter (v22.21, extended v22.23 shrink, v22.32 flat-mid shrink).
            // SELL at upper band when H4 bullish fly/shrink, BUY at lower band when H4 bearish.
            // v22.23: extended to shrink stages (513/523 with committed mid).
            // v22.32: 523&&mid==3 and 513&&mid==3 — shrink with flat mid carries bearish/bullish
            // structural bias still (mirrors RC14/v22.29 M30 logic for G0b-H4OPP). RC18 confirmed.
            // v22.33: also block when H4 in SQZ (400-499) with opposing mid (mid==2/4 for BUY block;
            // mid==1/5 for SELL block). H4-SQZ with bearish mid still carries bearish macro bias.
            // Confirmed: Apr-13 16:30 G0b-TOUCH BUY H4=423/mid=2 → -24.56. RC19.
            {
               int  H4_stg_gb = BB_datas[4].BBW_stage[LA];
               int  H4_mid_gb = BB_datas[4].BB_diffMid_Trend[LA];
               bool H4_fly_up_gb=(H4_stg_gb==511||H4_stg_gb==512)&&(H4_mid_gb==1||H4_mid_gb==5)
                                ||(H4_stg_gb==513&&(H4_mid_gb==1||H4_mid_gb==3||H4_mid_gb==5))
                                ||((H4_stg_gb>=400&&H4_stg_gb<500)&&(H4_mid_gb==1||H4_mid_gb==3||H4_mid_gb==5));
               bool H4_fly_dn_gb=(H4_stg_gb==521||H4_stg_gb==522)&&(H4_mid_gb==2||H4_mid_gb==4)
                                ||(H4_stg_gb==523&&(H4_mid_gb==2||H4_mid_gb==3||H4_mid_gb==4))
                                ||((H4_stg_gb>=400&&H4_stg_gb<500)&&(H4_mid_gb==2||H4_mid_gb==3||H4_mid_gb==4));
               if((cas_dir==1&&H4_fly_dn_gb)||(cas_dir==2&&H4_fly_up_gb)) {
                  Trade_info = "Gate:[G0b-H4OPP] TradeAct:"+IntegerToString(Trade_act)+" H4stg:"+H4_stg_gb+" H4mid:"+H4_mid_gb;
                  DrawGateLabel("[G0b-H4OPP]", close_prices[LA], BB_datas, GATE_CLR_H4, 1);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // M30 opposing filter (v22.25, extended v22.29): block cascade touch when M30 fly/shrink opposes direction.
            // BUY: 521/522 with mid2/4 — active bearish fly; 523 with mid2/3/4 — bearish shrink not yet reversing.
            // SELL: 511/512 with mid1/5 — active bullish fly; 513 with mid1/3/5 — bullish shrink not yet reversing.
            // v22.29 extension: 523&&mid==3 and 513&&mid==3 — shrink with flat mid has no reversal signal yet.
            // Confirmed RC14: Feb-26 07:30 M30=523/mid=3 BUY -4.02, Mar-03 03:00 M30=523/mid=3 BUY -45.36.
            {
               int  M30_stg_gb = BB_datas[2].BBW_stage[LA];
               int  M30_mid_gb = BB_datas[2].BB_diffMid_Trend[LA];
               bool M30_fly_dn_gb=(M30_stg_gb==521||M30_stg_gb==522)&&(M30_mid_gb==2||M30_mid_gb==4)
                                 ||(M30_stg_gb==523&&(M30_mid_gb==2||M30_mid_gb==3||M30_mid_gb==4));
               bool M30_fly_up_gb=(M30_stg_gb==511||M30_stg_gb==512)&&(M30_mid_gb==1||M30_mid_gb==5)
                                 ||(M30_stg_gb==513&&(M30_mid_gb==1||M30_mid_gb==3||M30_mid_gb==5));
               if((cas_dir==1&&M30_fly_dn_gb)||(cas_dir==2&&M30_fly_up_gb)) {
                  Trade_info = "Gate:[G0b-M30OPP] TradeAct:"+IntegerToString(Trade_act)+" M30stg:"+M30_stg_gb+" M30mid:"+M30_mid_gb;
                  DrawGateLabel("[G0b-M30OPP]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 1);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-SQZLOCK: H1+M30 both in SQZ AND both strictly sideway (mid==3) — G0c-SQZLOCK
            // condition applies but G0b returns before G0c evaluates. Only block when BOTH mids
            // are 3 (pure sideway, zero directional conviction). If either has a directional mid
            // (uptrend/downtrend/sideway-up/dn), the trade has macro conviction — allow through.
            // v22.27 original was H1_SQZ&&M30_SQZ (any mid) → over-filtered Feb-06 13:30 +47.79
            // and Mar-20 14:40 +93.06. Narrowed in v22.28 to both-mid==3 only.
            // Confirmed blocks: Feb-06 08:00 BUY H1_mid=3+M30_mid=3 → -42.99, Apr-15 17:35 → -14.64.
            {
               bool h1_sqz_gb  = (BB_datas[3].BBW_stage[LA]>=400 && BB_datas[3].BBW_stage[LA]<500);
               bool m30_sqz_gb = (BB_datas[2].BBW_stage[LA]>=400 && BB_datas[2].BBW_stage[LA]<500);
               bool h1_mid_flat= (BB_datas[3].BB_diffMid_Trend[LA]==3);
               bool m30_mid_flat=(BB_datas[2].BB_diffMid_Trend[LA]==3);
               if(h1_sqz_gb && m30_sqz_gb && h1_mid_flat && m30_mid_flat) {
                  Trade_info = "Gate:[G0b-SQZLOCK] TradeAct:"+IntegerToString(Trade_act)+" H1_SQZ+M30_SQZ+both_flat";
                  DrawGateLabel("[G0b-SQZLOCK]", close_prices[LA], BB_datas, GATE_CLR_PINK, 1);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-H1OPP: H1 committed fly opposing cascade direction (RC36, v22.46).
            // Cascade path parallel to G4b-H1OPP in shrink path. G0b-H1SQZDN covers H1-SQZ;
            // this gate covers H1 in committed fly (511/512/521/522) opposing cas_dir.
            // Includes mid=3 (flat) from the start — same structural reasoning as RC35.
            // Feb-10 03:30 SELL casTF=4, H1=512/mid=3 (bullish fly, flat mid) → -16.90; 0 wins lost.
            {
               int  H1_stg_hop = BB_datas[3].BBW_stage[LA];
               int  H1_mid_hop = BB_datas[3].BB_diffMid_Trend[LA];
               bool H1_fly_up_hop = (H1_stg_hop==511||H1_stg_hop==512)&&(H1_mid_hop==1||H1_mid_hop==3||H1_mid_hop==5);
               bool H1_fly_dn_hop = (H1_stg_hop==521||H1_stg_hop==522)&&(H1_mid_hop==2||H1_mid_hop==3||H1_mid_hop==4);
               if((cas_dir==1&&H1_fly_dn_hop)||(cas_dir==2&&H1_fly_up_hop)) {
                  Trade_info = "Gate:[G0b-H1OPP] TradeAct:"+IntegerToString(Trade_act)+" H1stg:"+H1_stg_hop+" H1mid:"+H1_mid_hop;
                  DrawGateLabel("[G0b-H1OPP]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 3);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-H1SQZDN: H1 SQZ with opposing mid in cascade path (RC25 v22.37, RC26 v22.38).
            // RC25: blocked H1-SQZ/mid=4 (sideway-dn) opposing BUY.
            // RC26: extended to mid=2 (full downtrend) — same structural gap, stronger bearish signal.
            // SELL side: mid=5 only (mid=1 has confirmed wins; do NOT extend).
            {
               int  H1_stg_h1dn = BB_datas[3].BBW_stage[LA];
               int  H1_mid_h1dn = BB_datas[3].BB_diffMid_Trend[LA];
               bool H1_sqz_opp_buy  = (H1_stg_h1dn>=400&&H1_stg_h1dn<500)&&(H1_mid_h1dn==4||H1_mid_h1dn==2);
               bool H1_sqz_opp_sell = (H1_stg_h1dn>=400&&H1_stg_h1dn<500)&&(H1_mid_h1dn==5);
               if((cas_dir==1&&H1_sqz_opp_buy)||(cas_dir==2&&H1_sqz_opp_sell)) {
                  Trade_info = "Gate:[G0b-H1SQZDN] TradeAct:"+IntegerToString(Trade_act)+" H1stg:"+H1_stg_h1dn+" H1mid:"+H1_mid_h1dn;
                  DrawGateLabel("[G0b-H1SQZDN]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 4);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-M5OPP: sole M5 shrink trigger with M5 mid opposing direction (RC15, v22.31).
            // When M5 is the ONLY shrink TF (cas_shrinkTF==0) and M5 itself is in opposing
            // shrink mid → the cascade trigger fights its own midtrend: BUY at M5 lower band
            // when M5 is bearish shrink/mid (523+mid2/4), SELL at upper when bullish (513+mid1/5).
            // Confirmed: Mar-03 05:00 BUY M5=523/mid=2 -63.53; Mar-04 15:15 BUY M5=523/mid=4 -41.43.
            if(cas_shrinkTF == 0) {
               int  m5_stg_gb  = BB_datas[0].BBW_stage[LA];
               int  m5_mid_gb  = BB_datas[0].BB_diffMid_Trend[LA];
               bool m5_opp_buy = (m5_stg_gb==523)&&(m5_mid_gb==2||m5_mid_gb==4);
               bool m5_opp_sel = (m5_stg_gb==513)&&(m5_mid_gb==1||m5_mid_gb==5);
               if((cas_dir==1&&m5_opp_buy)||(cas_dir==2&&m5_opp_sel)) {
                  Trade_info = "Gate:[G0b-M5OPP] TradeAct:"+IntegerToString(Trade_act)+" M5stg:"+m5_stg_gb+" M5mid:"+m5_mid_gb;
                  DrawGateLabel("[G0b-M5OPP]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 1);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-M5FLY: M5 in committed opposing fly when higher TF is cascade trigger (RC28b, v22.41).
            // When cas_shrinkTF > 0 (M5 is not the trigger) and M5 is in committed opposing fly
            // (521/522 for BUY direction; 511/512 for SELL direction), the fastest TF directly
            // contradicts the cascade direction. Confirmed: 5 losses -77.37, 1 win +2.41, net +74.96.
            if(cas_shrinkTF > 0) {
               int  m5_stg_mf     = BB_datas[0].BBW_stage[LA];
               bool m5_opp_buy_mf = (m5_stg_mf==521 || m5_stg_mf==522);
               bool m5_opp_sel_mf = (m5_stg_mf==511 || m5_stg_mf==512);
               if((cas_dir==1 && m5_opp_buy_mf) || (cas_dir==2 && m5_opp_sel_mf)) {
                  Trade_info = "Gate:[G0b-M5FLY] TradeAct:0 M5stg:"+IntegerToString(m5_stg_mf)+" cas_shrinkTF:"+IntegerToString(cas_shrinkTF);
                  DrawGateLabel("[G0b-M5FLY]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }
            // G0b-M5SHRKopp: M5 in opposing bearish/bullish shrink when higher TF is cascade trigger (v22.44, RC34)
            // Extends G0b-M5FLY (committed fly 521/522) to also cover M5=523 (bearish shrink) for BUY
            // and M5=513 (bullish shrink) for SELL, when mid still opposes direction (mid∈{2,3,4} for BUY;
            // mid∈{1,3,5} for SELL). If mid has reversed (mid=1 for BUY within 523), the reversal is genuine.
            // RC34: Jan-29 16:10 BUY at H1 lower band (cas_shrinkTF=3), M5=523/mid=3 → -43.37.
            if(cas_shrinkTF > 0) {
               int  m5_stg_sr  = BB_datas[0].BBW_stage[LA];
               int  m5_mid_sr  = BB_datas[0].BB_diffMid_Trend[LA];
               bool m5_shrk_opp_buy = (m5_stg_sr==523)&&(m5_mid_sr==2||m5_mid_sr==3||m5_mid_sr==4);
               bool m5_shrk_opp_sel = (m5_stg_sr==513)&&(m5_mid_sr==1||m5_mid_sr==3||m5_mid_sr==5);
               if((cas_dir==1 && m5_shrk_opp_buy) || (cas_dir==2 && m5_shrk_opp_sel)) {
                  Trade_info = "Gate:[G0b-M5SHRKopp] TradeAct:0 M5stg:"+IntegerToString(m5_stg_sr)+" M5mid:"+IntegerToString(m5_mid_sr)+" cas_shrinkTF:"+IntegerToString(cas_shrinkTF);
                  DrawGateLabel("[G0b-M5SHRKopp]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
                  Print("[TRADEINFO] " + Trade_info + "|act:0 atrsl:" + ATRSL1BUF.dir); return;
               }
            }

            // Band-touch entry
            Trade_act = (cas_dir==1) ? 1 : 2;
            Trade_sl   = GetATRSLStop(ATRSL1BUF, cas_dir);
            s_lastEntryWasCascade = true;   // v22.45: mark as cascade for G5-FADE logic
            s_lastEntryTrigTF     = (cas_shrinkTF >= 0) ? cas_shrinkTF : 0;
            s_lastEntryTime       = iTime(_Symbol, PERIOD_M5, 0);
            Trade_info = "Gate:[G0b-TOUCH] TradeAct:"+IntegerToString(Trade_act)+" TF:"+htf+" touch:"+cas_touch+" sl:"+DoubleToString(Trade_sl,_Digits);
            DrawGateLabel("[G0b-TOUCH]", close_prices[LA], BB_datas,
                           (cas_dir==1 ? GATE_CLR_BUY : GATE_CLR_SELL), 1);
            Print("[TRADEINFO] " + Trade_info + "|act:" + Trade_act + " atrsl:" + ATRSL1BUF.dir); return;
         }
         else {
            Trade_info = "Gate:[G0b-WAIT] TradeAct:"+IntegerToString(Trade_act)+" TF:"+(string)cas_shrinkTF;
            DrawGateLabel("[G0b-WAIT]", close_prices[LA], BB_datas, GATE_CLR_WAIT, 1);
         }
      }
   }

   // ── GATE 0c: H1 SQZ + (M30 compressed or M15 SQZ) → block ────
   // Extended from original M30+H1 both SQZ: now also covers the gap
   // where M30 exits SQZ→shrink while H1 is still fully compressed.
   {
      bool H1_sqz_c       = (BB_datas[3].BBW_stage[LA]>=400 && BB_datas[3].BBW_stage[LA]<500);
      bool M30_compressed = (BB_datas[2].BBW_stage[LA]>=400 && BB_datas[2].BBW_stage[LA]<500)
                         || (BB_datas[2].BBW_stage[LA]==513 || BB_datas[2].BBW_stage[LA]==523);
      bool M15_sqz_c      = (BB_datas[1].BBW_stage[LA]>=400 && BB_datas[1].BBW_stage[LA]<500);
      if(H1_sqz_c && (M30_compressed || M15_sqz_c)) {
         Trade_act  = 0;
         Trade_lots = 0.0;
         string sqz_tag = M30_compressed ? "M30_cmp" : "M15_SQZ";
         string g0c_seg = "Gate:[G0c-SQZLOCK] H1_SQZ:" + sqz_tag;
         Trade_info = (StringLen(Trade_info)==0)
            ? g0c_seg + " TradeAct:"+IntegerToString(Trade_act)
            : Trade_info + "| " + g0c_seg;
         DrawGateLabel("[G0c-SQZLOCK]", BB_datas[2].BB_Mid[LA], BB_datas, GATE_CLR_PINK, 2);
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

   // ── M5 FADING → EXIT ALL (v22.45: delayed + cascade-aware) ──────
   // #2: Delay G5-FADE — require 2 consecutive flat bars OR M15 also fading.
   //     A single M5 flat bar during active M15 trend is noise — don't exit yet.
   // #6: Cascade entries need M15 confirm even for 1-bar M5 flat (mean-reversion
   //     targets a band touch, not a trend; M5 flat mid-trade is expected noise).
   {
      int M5_cur  = BB_datas[0].BB_diffMid_Trend[LA];
      int M5_prev = BB_datas[0].BB_diffMid_Trend[LA_1];
      int M5_pp   = BB_datas[0].BB_diffMid_Trend[LA_2];
      int M15_cur = BB_datas[1].BB_diffMid_Trend[LA];
      bool m15_fading = (M15_cur >= 3);
      // Persistent flat: M5 stayed flat for 2 consecutive bars (strong confirmation)
      bool m5_flat2 = (M5_cur == 3 && M5_prev == 3);
      // Single-bar fade with M15 also fading (non-cascade standard path)
      bool fade_buy_1bar  = (M5_prev==1 && M5_cur==3 && m15_fading);
      bool fade_sell_1bar = (M5_prev==2 && M5_cur==3 && m15_fading);
      // Two-bar fade from prior trend (cascade and non-cascade both exit)
      bool fade_buy_2bar  = (M5_pp==1 && m5_flat2);
      bool fade_sell_2bar = (M5_pp==2 && m5_flat2);

      bool fire_fade_buy  = false;
      bool fire_fade_sell = false;
      if(s_lastEntryWasCascade) {
         // Cascade entries: M5 flat alone insufficient; require M15 also fading OR 2-bar persistence
         fire_fade_buy  = BUYS>0  && (fade_buy_2bar  || (M5_cur==3 && m15_fading));
         fire_fade_sell = SELLS>0 && (fade_sell_2bar || (M5_cur==3 && m15_fading));
      } else {
         fire_fade_buy  = BUYS>0  && (fade_buy_1bar  || fade_buy_2bar);
         fire_fade_sell = SELLS>0 && (fade_sell_1bar || fade_sell_2bar);
      }
      if(fire_fade_buy || fire_fade_sell) {
         Trade_act=7; Trade_lots=0.0;
         s_exitCooldown=POST_EXIT_COOLDOWN;
         Trade_info="Gate:[G5-FADE] TradeAct:"+IntegerToString(Trade_act)
                  +" M5:"+M5_prev+">"+M5_cur+" M15:"+M15_cur
                  +(s_lastEntryWasCascade?" cas":"");
         DrawGateLabel("[G5-FADE]", close_prices[LA], BB_datas, GATE_CLR_EXIT, 0);
         Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
      }
   }

   // ── SHRINK PATH ───────────────────────────────────────────────
   bool M5_shrink =(BB_datas[0].BBW_stage[LA]==513||BB_datas[0].BBW_stage[LA]==523);
   bool H4_shrink =(BB_datas[4].BBW_stage[LA]==513||BB_datas[4].BBW_stage[LA]==523);
   bool H1_shrink =(BB_datas[3].BBW_stage[LA]==513||BB_datas[3].BBW_stage[LA]==523);
   bool M30_shrink=(BB_datas[2].BBW_stage[LA]==513||BB_datas[2].BBW_stage[LA]==523);
   bool M15_shrink=(BB_datas[1].BBW_stage[LA]==513||BB_datas[1].BBW_stage[LA]==523);

   if(M5_shrink || H4_shrink || H1_shrink || M30_shrink || M15_shrink) {
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
         // M5 opposing during shrink → exit all
         int M5_now = BB_datas[0].BB_diffMid_Trend[LA];
         if((M5_now==2&&BUYS>0)||(M5_now==1&&SELLS>0)) {
            Trade_act=7; Trade_lots=0.0;
            s_exitCooldown=POST_EXIT_COOLDOWN;
            Trade_info += "| Gate:[G6-REV] M5:"+M5_now;
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
      bool nochain=false;
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
      else if((ltfUP||ltfDN)&&(htfShrk||htfSide))                                 nochain=true;

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
            // Allow only when M5 diffMidTrend explicitly confirms the direction;
            // M5 consensus adds the conviction that H4-SQZ cannot provide.
            int M5_mid_sqz = BB_datas[0].BB_diffMid_Trend[LA];
            bool M5_confirms = (direction==1 && (M5_mid_sqz==1||M5_mid_sqz==5))
                            || (direction==2 && (M5_mid_sqz==2||M5_mid_sqz==4));
            Trade_info = "Gate:[H4-SQZ] TradeAct:"+IntegerToString(Trade_act)
                       + " M5mid:"+M5_mid_sqz;
            DrawGateLabel("[H4-SQZ]", BB_datas[4].BB_Mid[LA], BB_datas, GATE_CLR_H4, 4);
            if(!M5_confirms) { direction = 0; }
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

      if(direction != 0) {
         Trade_act = (direction==1) ? 1 : 2;
         Trade_sl  = GetATRSLStop(ATRSL1BUF, direction);
         s_lastEntryWasCascade = false;          // v22.45
         // L2H depth sizing: highest flying TF in chain drives lot size (v22.42)
         // l2h=0 (M5 only) → 0.5×; l2h=1 (M15+) → 0.75×; l2h=2+ (M30+) → 1.0×
         int    l2h      = MathMax(L2H_flyUP_TF, L2H_flyDN_TF);
         s_lastEntryTrigTF = l2h;               // v22.45: L2H chain depth = effective trigger TF
         double l2hMulti = (l2h>=2) ? 1.0 : (l2h>=1) ? 0.75 : 0.5;
         int    H4_stg_l = BB_datas[4].BBW_stage[LA];
         if((H4_stg_l==513||H4_stg_l==523) && l2hMulti > 0.75) l2hMulti = 0.75;
         double vol_min  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
         double vol_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
         Trade_lots = MathMax(vol_min, MathRound(baseLot*l2hMulti/vol_step)*vol_step);
         Trade_info += "| Gate:[FLY] dir:"+direction
                     + " sl:"+DoubleToString(Trade_sl,_Digits)
                     + " H2L:"+H2L_flyUP_TF+"/"+H2L_flyDN_TF
                     + " L2H:"+L2H_flyUP_TF+"/"+L2H_flyDN_TF
                     + " l2hX:"+DoubleToString(l2hMulti,2)
                     + " lots:"+DoubleToString(Trade_lots,2);
      }
      else {
         string g7_tag = nochain ? "[G7-NOCHAIN]" : "[G7-NEUTRAL]";
         Trade_info += "| Gate:" + g7_tag;
         DrawGateLabel(g7_tag, BB_datas[0].BB_Mid[LA], BB_datas, GATE_CLR_NOISE, 0);
      }
   }

   // Final: if act=1/2 but no lot → clear
   if(Trade_act==1||Trade_act==2) {
      if(Trade_lots < SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)) {
         Trade_act=0; Trade_lots=0.0; Trade_info += "| Gate:[G7-SUPPRESSED]";
      }
   }

   // ── G7-NOTM15BAR: only allow shrink/fly entries on the last M5 bar of an M15 period (v22.45, #1)
   // Reduces M5 noise by gating entries to the bar that closes with the M15 bar — providing
   // a natural M15-synchronized confirmation window. Cascade entries (G0b-TOUCH) are exempt
   // because they return early and never reach this check.
   if(Trade_act==1 || Trade_act==2) {
      datetime m15_start = iTime(_Symbol, PERIOD_M15, 0);
      datetime m5_start  = iTime(_Symbol, PERIOD_M5,  0);
      bool is_last_m5 = (m5_start - m15_start >= (datetime)(PeriodSeconds(PERIOD_M15) - PeriodSeconds(PERIOD_M5)));
      if(!is_last_m5) {
         Trade_act = 0; Trade_lots = 0.0;
         Trade_info += "| Gate:[G7-NOTM15BAR] m5off:"+(string)(int)(m5_start-m15_start);
         DrawGateLabel("[G7-NOTM15BAR]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
      }
   }

   // ── FIX A PHASE 1: two-phase reversal interception ───────────
   // If a reversal signal fires against an open opposite position,
   // close only now; Phase 2 re-confirms after MIN_HOLD_BARS bars.
   if(Trade_act == 1 && SELLS > 0) {
      s_pendingBuy  = true; s_pendingSell = false;
      s_pendingTime = iTime(_Symbol, PERIOD_M5, 0);
      Trade_act = 7; Trade_lots = 0.0;
      Trade_info += "| Gate:[PHASE1-BUY]";
      DrawGateLabel("[PHASE1-BUY]", close_prices[LA], BB_datas, GATE_CLR_WAIT, 0);
      Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
   }
   else if(Trade_act == 2 && BUYS > 0) {
      s_pendingSell = true; s_pendingBuy = false;
      s_pendingTime = iTime(_Symbol, PERIOD_M5, 0);
      Trade_act = 7; Trade_lots = 0.0;
      Trade_info += "| Gate:[PHASE1-SELL]";
      DrawGateLabel("[PHASE1-SELL]", close_prices[LA], BB_datas, GATE_CLR_WAIT, 0);
      Print("[TRADEINFO] " + Trade_info + "|act:7 atrsl:" + ATRSL1BUF.dir); return;
   }

   // ── MIN HOLD BARS — dynamic by last entry trigger TF (v22.45, #3) ──
   // M5-triggered: 3 bars; M15: 6; M30: 12; H1+: 18
   if(Trade_act == 1 || Trade_act == 2) {
      int barsSinceLast = (s_lastEntryTime == 0) ? 999 :
         (int)((iTime(_Symbol,PERIOD_M5,0) - s_lastEntryTime) / PeriodSeconds(PERIOD_M5));
      int dynMinHold = DynMinHold(s_lastEntryTrigTF);

      if(barsSinceLast < dynMinHold) {
         Trade_act  = 0;
         Trade_lots = 0.0;
         Trade_info += "| Gate:[G7-TOOSOON] bars:"+(string)barsSinceLast+"<"+(string)dynMinHold;
         Stats_RecordBlock(Trade_info);
         DrawGateLabel("[G7-TOOSOON]", close_prices[LA], BB_datas, GATE_CLR_NOISE, 0);
      }
      else {
         // Record entry time when act is confirmed
         s_lastEntryTime = iTime(_Symbol, PERIOD_M5, 0);
      }
   }

   Print("[TRADEINFO] "+Trade_info+"|act:"+Trade_act+" atrsl:"+ATRSL1BUF.dir);
}