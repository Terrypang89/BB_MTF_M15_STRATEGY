#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "38.13"

#define HAS_TOFYSIDEWAY_LADDER
//+------------------------------------------------------------------+
//| TofySidewayLadder.mqh   -- DIAGNOSTIC ONLY                        |
//|                                                                  |
//| Computes the proposed sequential sideway LADDER and draws a label |
//| on every M15 bar so the flow can be verified visually.            |
//|                                                                  |
//| IT DOES NOT TRADE AND DOES NOT WRITE sideway_selected.            |
//| It writes only its own field so the existing detector and DMONLY  |
//| are completely unaffected. Run both in parallel, compare, and     |
//| only then decide whether the ladder should drive anything.        |
//|                                                                  |
//| LADDER (each step needs the PREVIOUS bar one level below):        |
//|   state 1  M15 : A15 and B15                                      |
//|   state 2  M30 : prev==1 and A30 and B30                          |
//|   state 3  H1  : prev==2 and A1H and B1H and C1H                  |
//|                                                                  |
//|   A15 = (clus0[LA] < clus0[LA_1] < clus0[LA_2]) OR                |
//|         (clus0[LA] < CL_NEAR and clus0[LA_1] < CL_NEAR)           |
//|   B15 = stage[1][LA] in (512,523,4xx) OR                          |
//|         (dmid[1][LA] < dmid[1][LA_1] < dmid[1][LA_2])             |
//|   A30/B30 same shape on clus1 and index 2                         |
//|   A1H = stage[3][LA] in (512,523,4xx) OR dbbw[3] decreasing       |
//|   B1H = clus2[LA] < clus2[LA_1] < clus2[LA_2]                     |
//|   C1H = clus1[LA] < CL_NEAR and clus1[LA_1] < CL_NEAR             |
//|                                                                  |
//| MEASURED on 20260712_clean.log (baseline QUIET 37.8%):            |
//|   state 1  n=2904  QUIET 41.4%  (+3.6)                            |
//|   state 2  n= 948  QUIET 48.0%  (+10.2)   <- best                 |
//|   state 3  n= 229  QUIET 41.0%  (+3.2)    <- DEGRADES             |
//|   current S_ flag  n=1681  QUIET 53.9%  (+16.1)                   |
//| On the 2026.02.03 12:40 - 02.04 02:05 choppy range (50 bars):     |
//|   current S_ covered  6/50 (12%)                                  |
//|   ladder state>=1    23/50 (46%)  but it fires on 38% of ALL bars |
//|                                                                  |
//| FIELD NAMES: BBW_stage and BB_midline_Cluster are confirmed from  |
//| existing code. BB_diffMid and BB_diffBBW are INFERRED from the    |
//| log field names diffMid_M15 / diffBBW_H1 -- if the compiler       |
//| rejects them, substitute the real struct member names.            |
//+------------------------------------------------------------------+

//--- ladder settings
bool   SL_Draw      = true;     // draw the ladder label
bool   SL_WriteLog  = true;     // emit [LADDER] log lines
int    SL_FontSize  = 10;
double SL_Angle     = 90.0;     // OBJPROP_ANGLE is a DOUBLE property
double CL_NEAR      = 10.5;     // 10.0 rejected clus1 = 10.1 by 0.1 and broke
                                // the ladder chain. 10.5 costs +89 bars and takes
                                // the 2026.02.03 window from 16/50 to 27/50.
//+------------------------------------------------------------------+
//| TRADE STRATEGY (optional)                                        |
//|                                                                  |
//| Trade_Strategy() below is DMONLY with one substitution:    |
//| the sideways exit fires on the LADDER (SL_state[LA] >= 2) instead |
//| of the TofySideway S_ flag. Everything else - entries, reversals, |
//| priority order, the once-per-bar guard - is identical to          |
//| TofyTrade_DMonly.mqh.                                             |
//|                                                                   |
//| SL_UseTradeStrategy = false  -> the function returns HOLD         |
//|                                 immediately and changes nothing.  |
//| SL_UseTradeStrategy = true   -> the ladder drives the exits.      |
//|                                                                   |
//| MEASURED against references/SIDEWAY_LABELS_FEB.md (858 of 1830    |
//| February bars labelled sideway):                                  |
//|   TofySideway S_   precision 82.4%  recall 33.2%  fires 346       |
//|   ladder state>=2  precision 70.4%  recall 60.3%  fires 734       |
//| The ladder fires roughly TWICE as often. The DMONLY churn         |
//| analysis found 844 trades held 1-5 bars lost -$2,258 while 276    |
//| held 6+ bars made +$3,227 - so more exits means shorter holds,    |
//| which has been the LOSING direction. Whether the ladder's better  |
//| recall outweighs that is exactly what this is here to measure.    |
//| It has NOT been measured yet.                                     |
//+------------------------------------------------------------------+
bool   SL_UseTradeStrategy = false;   // off by default - changes nothing until enabled

//--- which signal drives the sideways exit when the above is true
//---   0 = ladder only          SL_state[LA] >= 2
//---   1 = TofySideway only     sideway_selected[LA] > 0   (= plain DMONLY)
//---   2 = BOTH must agree      fewest exits, longest holds
//---   3 = EITHER fires         most exits
//---   4 = HAND LABELS          hindsight ceiling, NOT tradeable
int    SL_ExitMode = 0;

bool   SL_UseH1     = false;    // measured to DEGRADE the ladder; off by default
double SL_diffmid_m15 = 3;
double SL_diffmid_m30 = 1.5;

//--- LEVEL 1 evidence gate. Measured (L2Mode 0, BreakoutMode 1):
//---   0  A15 && (S15 || C15)   n=3158 (42%) lift +11.2  window 25/50  enrich 1.20x
//---   1  A15 && C15            n=3139 (41%) lift +11.5  window 25/50  enrich 1.21x  <- default
//---   2  A15 && S15            n=2353 (31%) lift +13.4  window 21/50  enrich 1.36x
//---   3  A15 && S15 && C15     n=2334 (31%) lift +13.8  window 21/50  enrich 1.37x
//--- Mode 1 beats mode 0 on lift AND enrichment at identical window coverage, and
//--- removes a false positive at 2026.02.04 05:15-05:30 where S15 was true while
//--- price ran 23-30 points.
int    SL_L1Mode = 1;

//--- LEVEL 2 evidence gate (always ANDed with prev >= 1 and A30):
//---   0  S30 || C30 || W30     n=3139 (41%) lift +11.5  window 25/50  <- default
//---   1  S30 || C30            n=2701 (35%) lift +13.3  window 19/50
//---   2  C30 only              n=2384 (31%) lift +14.7  window 11/50
//--- Higher modes are more precise but cover the target range worse.
int    SL_L2Mode = 0;

//--- A close outside the M15 band means the range has broken, so the sideway
//--- state is cancelled. MEASURED (with CL_NEAR 10.5):
//---   no cancel   n=3756 (49% of bars) lift +8.4
//---   M30 cancel  n=3145 (41% of bars) lift +9.8
//---   M15 cancel  n=2891 (38% of bars) lift +12.1   <- used here
//--- Sequential variants were worse: M15-then-M30 +9.2, M15-AND-M30 +10.0.
//--- M15 bands are tighter: they break earlier and re-contain earlier, which
//--- tracks price better than the lagging M30 band.
//--- Breakout cancel mode. A close outside the M15 band means the range broke.
//--- MEASURED (CL_NEAR 10.5, baseline QUIET 37.8%):
//---   0 off                n=3756 (49%) lift  +8.4  window 27/50  flips   0
//---   1 brk               n=2891 (38%) lift +12.1  window 21/50  flips 887  <- default
//---   2 brk 2 bars        n=3423 (45%) lift  +9.5  window 22/50  flips 406
//---   3 brk AND !B15      n=3657 (48%) lift  +9.4  window 21/50  flips 172
//--- Mode 1 is the most precise but flickers (flag toggles on ~12% of bars).
//--- Modes 2 and 3 are steadier and cost ~2.7 lift points. Flicker is cosmetic while
//--- this module drives nothing; it would matter if it ever drove an exit.
int    SL_BreakoutMode = 1;

//--- W30 dbbw < 1 fires +4.4 and is now part of the level-2 evidence gate.
//--- Threshold value barely matters: <0 <1 <2 <5 all give the same result.
double SL_diffbbw_m15 = 1.0;
double SL_diffbbw_m30 = 1.0;    // W30 threshold

//--- add near the other settings
bool SL_ShowFails = true;    // draw gray L0-A/L0-B labels for undetected bars


//+------------------------------------------------------------------+
//| HAND-LABELLED SIDEWAY RANGES (visual overlay + optional signal)  |
//|                                                                  |
//| The ranges from references/SIDEWAY_LABELS_FEB.md.                |
//|                                                                  |
//| TWO uses, both opt-in:                                            |
//|   SL_DrawUserLabels  - draw them as rectangles behind the candles |
//|   SL_ExitMode == 4   - use them AS the sideway signal             |
//|                                                                  |
//| MEASURED (February, DMONLY entries, gross):                       |
//|   labels as the signal   58 trades  +415.36   <- CEILING          |
//|   best ladder setting    64 trades   -66.13                       |
//|   TofySideway S_ flag   159 trades   -70.74                       |
//|   no sideway exit       114 trades  -636.37   <- FLOOR            |
//|                                                                   |
//| ############ THE LABELS ARE HINDSIGHT ############                |
//| SL_ExitMode 4 is NOT TRADEABLE. It knows the answer in advance.   |
//| It exists only to measure the ceiling on a backtest. Never run it |
//| forward, and never treat +415.36 as a target - it is headroom.    |
//| ##################################################                |
//+------------------------------------------------------------------+
bool   SL_DrawUserLabels = false;   // draw the ranges on the chart
color  SL_LabelColor     = clrDarkSlateGray;
bool   SL_LabelFill      = true;

//--- Hand-labelled sideway ranges from references/SIDEWAY_LABELS_FEB.md
//--- Extend this array when a new month is labelled. Format "YYYY.MM.DD HH:MM".
#define SL_LABEL_COUNT 27
string SL_LabelStart[SL_LABEL_COUNT] = {
   "2026.02.02 15:00",   // L1
   "2026.02.03 13:30",   // L2
   "2026.02.04 08:30",   // L3
   "2026.02.05 08:30",   // L4
   "2026.02.06 09:40",   // L5
   "2026.02.06 20:30",   // L6
   "2026.02.09 06:15",   // L7
   "2026.02.10 03:45",   // L8
   "2026.02.11 07:30",   // L9
   "2026.02.11 20:45",   // L10
   "2026.02.12 03:45",   // L11
   "2026.02.12 21:45",   // L12
   "2026.02.13 06:45",   // L13
   "2026.02.13 23:45",   // L14
   "2026.02.16 13:15",   // L15
   "2026.02.17 10:45",   // L16
   "2026.02.17 19:25",   // L17
   "2026.02.18 08:45",   // L18
   "2026.02.19 01:45",   // L19
   "2026.02.19 14:45",   // L20
   "2026.02.19 21:30",   // L21
   "2026.02.20 12:45",   // L22
   "2026.02.23 06:45",   // L23
   "2026.02.24 07:00",   // L24
   "2026.02.24 21:30",   // L25
   "2026.02.25 06:15",   // L26
   "2026.02.27 01:45"    // L27
};
string SL_LabelEnd[SL_LABEL_COUNT] = {
   "2026.02.03 01:00",   // L1
   "2026.02.04 02:00",   // L2
   "2026.02.04 16:15",   // L3
   "2026.02.05 21:15",   // L4
   "2026.02.06 13:00",   // L5
   "2026.02.06 23:45",   // L6
   "2026.02.09 16:30",   // L7
   "2026.02.11 01:15",   // L8
   "2026.02.11 11:30",   // L9
   "2026.02.11 23:45",   // L10
   "2026.02.12 18:00",   // L11
   "2026.02.13 03:00",   // L12
   "2026.02.13 15:45",   // L13
   "2026.02.16 04:15",   // L14
   "2026.02.17 01:45",   // L15
   "2026.02.17 15:30",   // L16
   "2026.02.18 03:45",   // L17
   "2026.02.18 14:45",   // L18
   "2026.02.19 07:15",   // L19
   "2026.02.19 16:45",   // L20
   "2026.02.20 07:45",   // L21
   "2026.02.20 14:45",   // L22
   "2026.02.23 16:15",   // L23
   "2026.02.24 14:15",   // L24
   "2026.02.25 02:45",   // L25
   "2026.02.25 17:45",   // L26
   "2026.02.27 15:00"    // L27
};

//+------------------------------------------------------------------+
//| Is this bar inside a hand-labelled range?                        |
//| Used only when SL_ExitMode == 4. See the hindsight warning above.|
//+------------------------------------------------------------------+
bool SL_InUserLabel(datetime t)
{
   for(int i = 0; i < SL_LABEL_COUNT; i++)
   {
      datetime t1 = StringToTime(SL_LabelStart[i]);
      datetime t2 = StringToTime(SL_LabelEnd[i]);
      if(t1 > 0 && t2 > 0 && t >= t1 && t <= t2) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Draw the labelled ranges. Call ONCE (OnInit, or guarded by a     |
//| static flag) - not per bar.                                      |
//+------------------------------------------------------------------+
void SL_DrawUserLabelRanges()
{
   if(!SL_DrawUserLabels) return;

   for(int i = 0; i < SL_LABEL_COUNT; i++)
   {
      datetime t1 = StringToTime(SL_LabelStart[i]);
      datetime t2 = StringToTime(SL_LabelEnd[i]);
      if(t1 <= 0 || t2 <= 0 || t2 <= t1) continue;

      string name = "SLLBL_" + IntegerToString(i + 1);
      if(ObjectFind(0, name) >= 0) continue;

      int b1 = iBarShift(_Symbol, PERIOD_M15, t2, false);   // newer = smaller shift
      int b2 = iBarShift(_Symbol, PERIOD_M15, t1, false);   // older = larger shift
      if(b1 < 0 || b2 < 0 || b2 < b1) continue;

      //--- scan bars directly. iHighest/iLowest are ambiguous here because
      //--- mql4compat.mqh declares int-typed overloads alongside the MQL5
      //--- built-ins, so the compiler cannot resolve the call.
      double hi = 0.0, lo = 0.0;
      for(int b = b1; b <= b2; b++)
      {
         double h = iHigh(_Symbol, PERIOD_M15, b);
         double l = iLow (_Symbol, PERIOD_M15, b);
         if(h <= 0.0 || l <= 0.0) continue;
         if(hi == 0.0 || h > hi) hi = h;
         if(lo == 0.0 || l < lo) lo = l;
      }
      if(hi <= 0.0 || lo <= 0.0 || hi <= lo) continue;

      if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, lo, t2, hi)) continue;
      ObjectSetInteger(0, name, OBJPROP_COLOR,      SL_LabelColor);
      ObjectSetInteger(0, name, OBJPROP_FILL,       SL_LabelFill);
      ObjectSetInteger(0, name, OBJPROP_BACK,       true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetString (0, name, OBJPROP_TOOLTIP,
                       "LABEL L" + IntegerToString(i + 1) + "  " +
                       SL_LabelStart[i] + " -> " + SL_LabelEnd[i]);
   }
}

//--- ladder state history: [LA]=current, ages toward [LA_4]
int SL_state[5];

//+------------------------------------------------------------------+
//| stage counts as a sideway-ish stage                              |
//+------------------------------------------------------------------+
bool SL_StageOK(int st)
{  return (st == 512 || st == 523 || (st >= 400 && st <= 499)); }

//+------------------------------------------------------------------+
//| Compute the ladder for the current bar. Call ONCE per M15 bar,   |
//| AFTER BBDatas_Midline_Cluster has updated BB_midline_Cluster.    |
//+------------------------------------------------------------------+
void SL_Update(BB_MTF_Impact_struct &BBTFImpact,
               BB_MTF_Data_struct   &BB_datas[])
{
   //--- age the history
   SL_state[LA_4] = SL_state[LA_3];
   SL_state[LA_3] = SL_state[LA_2];
   SL_state[LA_2] = SL_state[LA_1];
   SL_state[LA_1] = SL_state[LA];
   SL_state[LA]   = 0;

   int prev = SL_state[LA_1];

   //--- cluster distances, current and two bars back
   double c0  = BBTFImpact.BB_midline_Cluster[0][LA];
   double c0a = BBTFImpact.BB_midline_Cluster[0][LA_1];
   double c0b = BBTFImpact.BB_midline_Cluster[0][LA_2];
   double c1  = BBTFImpact.BB_midline_Cluster[1][LA];
   double c1a = BBTFImpact.BB_midline_Cluster[1][LA_1];
   double c1b = BBTFImpact.BB_midline_Cluster[1][LA_2];
   double c2  = BBTFImpact.BB_midline_Cluster[2][LA];
   double c2a = BBTFImpact.BB_midline_Cluster[2][LA_1];
   double c2b = BBTFImpact.BB_midline_Cluster[2][LA_2];
   double c3  = BBTFImpact.BB_midline_Cluster[3][LA];
   double c3a = BBTFImpact.BB_midline_Cluster[3][LA_1];
   double c3b = BBTFImpact.BB_midline_Cluster[3][LA_2];

   double dm1  = MathAbs(BB_datas[1].BB_diffMid[LA]);
   double dm1a = MathAbs(BB_datas[1].BB_diffMid[LA_1]);
   double dm1b = MathAbs(BB_datas[1].BB_diffMid[LA_2]);
   double dm2  = MathAbs(BB_datas[2].BB_diffMid[LA]);
   double dm2a = MathAbs(BB_datas[2].BB_diffMid[LA_1]);
   double dm2b = MathAbs(BB_datas[2].BB_diffMid[LA_2]);
   double dm3  = MathAbs(BB_datas[3].BB_diffMid[LA]);
   double dm3a = MathAbs(BB_datas[3].BB_diffMid[LA_1]);
   double dm3b = MathAbs(BB_datas[3].BB_diffMid[LA_2]);

   //--- LEVEL 1 predicates, named individually (lift measured alone)
   bool A15 = ((c0 < c0a && c0a < c0b) || (c0 < CL_NEAR && c0a < CL_NEAR));  // +4.5
   bool S15 = SL_StageOK((int)BB_datas[1].BBW_stage[LA]);                    // +3.3
   bool C15 = (dm1 < SL_diffmid_m15 && dm1a < SL_diffmid_m15);               // +5.3
   bool D15 = (dm1 < dm1a && dm1a < dm1b);                                   // no use
   bool W15 = (BB_datas[1].BB_diffBBW[LA]   < SL_diffbbw_m15
            && BB_datas[1].BB_diffBBW[LA_1] < SL_diffbbw_m15);  

   bool lvl1 = false;
   if(SL_L1Mode == 0)      lvl1 = (A15 && (S15 || C15));
   else if(SL_L1Mode == 1) lvl1 = (A15 && C15);                              // current use
   else if(SL_L1Mode == 2) lvl1 = (A15 && S15);
   else if(SL_L1Mode == 3) lvl1 = (A15 && S15 && C15);
   else if(SL_L1Mode == 4) lvl1 = (A15 && (S15 || C15) && (D15 || C15));
   else if(SL_L1Mode == 5) lvl1 = (A15 && (S15 || W15) && (D15 || C15));

   if(lvl1) SL_state[LA] = 1;

   //--- LEVEL 2 predicates, named individually
   bool A30 = ((c1 < c1a && c1a < c1b) || (c1 < CL_NEAR && c1a < CL_NEAR));  // +5.4
   bool S30 = SL_StageOK((int)BB_datas[2].BBW_stage[LA]);                    // +4.1
   bool C30 = (dm2 < SL_diffmid_m30 && dm2a < SL_diffmid_m30);               // +10.9
   bool D30 = (dm2 < dm2a && dm2a < dm2b);                                   // no use
   bool W30 = (BB_datas[2].BB_diffBBW[LA]   < SL_diffbbw_m30
            && BB_datas[2].BB_diffBBW[LA_1] < SL_diffbbw_m30);               // +4.4

   bool ev30 = false;
   if(SL_L2Mode == 0)      ev30 = (S30 || C30 || W30);                       // current use 
   else if(SL_L2Mode == 1) ev30 = (S30 || C30);
   else if(SL_L2Mode == 2) ev30 = C30;
   else if(SL_L2Mode == 3) ev30 = (A30 && (S30 || C30));

   if(prev >= 1 && A30 && ev30) SL_state[LA] = 2;

   //--- BREAKOUT CANCELS the sideway state (M15 band, index 1)
   bool brk = false;
   if(SL_BreakoutMode > 0)
   {
      double close_now  = iClose(_Symbol, PERIOD_M5, 0);
      double close_prev = iClose(_Symbol, PERIOD_M5, 3);   // 3 M5 bars = 1 M15 bar back

      bool raw  = (close_now  > BB_datas[1].BBUppLV[LA]
                || close_now  < BB_datas[1].BBLowLV[LA]);
      bool raw1 = (close_prev > BB_datas[1].BBUppLV[LA_1]
                || close_prev < BB_datas[1].BBLowLV[LA_1]);

      if(SL_BreakoutMode == 1)      brk = raw;
      else if(SL_BreakoutMode == 2) brk = (raw && raw1);
      else if(SL_BreakoutMode == 3) brk = (raw && !C15);                   // current use
      else if(SL_BreakoutMode == 4) brk = (raw && !C15 && !W15);

      if(brk) SL_state[LA] = 0;
   }

   // extra adding to test
   // if(prev >= 1 && W15 && SL_state[LA] == 0) SL_state[LA] = 1;

   //--- H1 block -> state 3 (needs previous bar == 2). OFF by default.
   bool A1H = false, B1H = false, C1H = false;
   if(SL_UseH1)
   {
      A1H = ( SL_StageOK((int)BB_datas[3].BBW_stage[LA])
           || (BB_datas[3].BB_diffBBW[LA] < BB_datas[3].BB_diffBBW[LA_1]
            && BB_datas[3].BB_diffBBW[LA_1] < BB_datas[3].BB_diffBBW[LA_2]) );
      B1H = (c2 < c2a && c2a < c2b) || (c3 < c3a && c3a < c3b);
      C1H = (c1 < CL_NEAR && c1a < CL_NEAR);
      // if(prev == 2 && A1H && B1H && C1H) SL_state[LA] = 3;
      if(prev >= 1 && A1H && B1H && C1H) SL_state[LA] = 3;
   }

   //--- why did it fail? (for the label and log)
   //--- report the gate that blocked the level ACTUALLY reached.
   string why = "";
   if(SL_state[LA] == 0)
   {
      if(brk)       why = "brk";
      else if(!A15) why = "A15";
      else          why = "ev15";
   }
   else if(SL_state[LA] == 1)
   {
      if(prev < 1)  why = "prev";
      else if(!A30) why = "A30";
      else          why = "ev30";
   }

   //--- draw
   if(SL_Draw)
   {
      double mid = BB_datas[1].BBMidLV[LA];
      datetime t = iTime(_Symbol, PERIOD_M15, 0);

      // skip state-0 bars only when SL_ShowFails is off
      if(mid > 0.0 && t > 0 && (SL_state[LA] > 0 || SL_ShowFails))
      {
         string txt = "L" + IntegerToString(SL_state[LA]);
         if(why != "") txt += "-" + why;

         string name = txt + "_" + IntegerToString((int)t);   // ID only, one label per bar
         if(ObjectFind(0, name) < 0)
         {
            color col;
            if(SL_state[LA] == 3)      col = clrAqua;
            else if(SL_state[LA] == 2) col = clrLime;
            else if(SL_state[LA] == 1) col = clrYellow;
            else                       col = clrGray;

            if(ObjectCreate(0, name, OBJ_TEXT, 0, t, mid))
            {
               ObjectSetString (0, name, OBJPROP_TEXT,     txt);
               ObjectSetInteger(0, name, OBJPROP_COLOR,    col);
               ObjectSetInteger(0, name, OBJPROP_FONTSIZE, SL_FontSize);
               ObjectSetDouble (0, name, OBJPROP_ANGLE,    SL_Angle);
               ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_UPPER);
               ObjectSetInteger(0, name, OBJPROP_BACK,     false);
            }
         }
      }
   }

   //--- log, so the chart can be cross-checked against the numbers
   if(SL_WriteLog)
   {
      Print("[LADDER] state:[", SL_state[LA],
            "] prev:[", prev,
            "] why:[", why,
            "] L1m:[", SL_L1Mode, "] L2m:[", SL_L2Mode,
            "] A15:[", A15, "] S15:[", S15, "] C15:[", C15,
            "] A30:[", A30, "] S30:[", S30, "] C30:[", C30, "] W30:[", W30,
            "] brkmode:[", SL_BreakoutMode, "] brk:[", brk,
            "] c0:[", DoubleToString(c0,1),
            "] c1:[", DoubleToString(c1,1),
            "] c2:[", DoubleToString(c2,1),
            "] ws15:[", (int)BB_datas[1].BBW_stage[LA],
            "] ws30:[", (int)BB_datas[2].BBW_stage[LA], "]");
   }
}


//+------------------------------------------------------------------+
//| Trade_Strategy                                            |
//|                                                                  |
//| SAME SIGNATURE as TofyTrade6 / TofyTrade_DMonly Trade_Strategy,  |
//| but a DIFFERENT NAME so both can be included without colliding.  |
//| Dispatch from the EA:                                            |
//|                                                                  |
//|     if(SL_UseTradeStrategy)                                      |
//|        Trade_Strategy( ...same args... );                 |
//|     else                                                         |
//|        Trade_Strategy( ...same args... );                        |
//|                                                                  |
//| REQUIREMENT: SL_Update() must already have run for this bar, or  |
//| SL_state[LA] is stale. In Tofu_EA_Simple_V7 SL_Update is called  |
//| inside the M15 gate before the Trade_Strategy dispatch.          |
//+------------------------------------------------------------------+
void Trade_Strategy(
   BB_MTF_Data_struct      &BB_datas[],
   ATRSLBUF_struct         &ATRSL1BUF,
   BB_MTF_Impact_struct    &BBTFImpact,
   ENUM_Trade_Act          &Trade_act,   // OUT: 0=hold 1=BUY 2=SELL 7=exit_all
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
   Trade_act = 0; Trade_info = ""; Trade_lots = baseLot; Trade_sl = 0.0;

   //--- master switch: do nothing at all unless explicitly enabled
   if(!SL_UseTradeStrategy) return;

   //--- Once-per-bar guard
   static datetime sl_lastBar = 0;
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur == sl_lastBar) { Trade_info = ""; return; }
   sl_lastBar = cur;

   //--- inputs
   double dm      = BB_datas[1].BB_diffMid_Trend[LA];      // index 1 = M15, current
   int    sflag   = (int)BBTFImpact.sideway_selected[LA];  // TofySideway S_ (LA = current)
   int    ladder  = SL_state[LA];                          // ladder state for this bar

   bool sw_flag   = (sflag  > 0);
   bool sw_ladder = (ladder >= 2);

   bool sw = false;
   if(SL_ExitMode == 0)      sw = sw_ladder;
   else if(SL_ExitMode == 1) sw = sw_flag;
   else if(SL_ExitMode == 2) sw = (sw_flag && sw_ladder);
   else if(SL_ExitMode == 3) sw = (sw_flag || sw_ladder);
   else if(SL_ExitMode == 4) sw = SL_InUserLabel(cur);   // HINDSIGHT - ceiling only

   bool dm_up   = (dm == 1.0 || dm == 5.0);
   bool dm_down = (dm == 2.0 || dm == 4.0);

   bool inLong  = (BUYS  > 0);
   bool inShort = (SELLS > 0);
   bool flat    = (!inLong && !inShort);

   Trade_info = "[LADTRADE] dm:" + DoubleToString(dm,1)
              + " LAD:"   + IntegerToString(ladder)
              + " S_:"    + IntegerToString(sflag)
              + " XM:"    + IntegerToString(SL_ExitMode)
              + " BUYS:"  + IntegerToString(BUYS)
              + " SELLS:" + IntegerToString(SELLS);

   //================================================================
   // PRIORITY 1 - SIDEWAYS EXIT. Close all. Exit beats entry.
   //================================================================
   if(sw)
   {
      if(!flat)
      {
         Trade_act = 7;                       // exit_all
         Trade_info += " [LAD]SIDEWAYS_EXIT";
      }
      return;   // sideway bar: never enter
   }

   //================================================================
   // PRIORITY 2 - REVERSAL (opposite dm closes; NO same-bar re-entry)
   //================================================================
   if(inLong && dm_down)
   {
      Trade_act = 7;
      Trade_info += " [LAD]REVERSAL_DN";
      return;
   }
   if(inShort && dm_up)
   {
      Trade_act = 7;
      Trade_info += " [LAD]REVERSAL_UP";
      return;
   }

   //================================================================
   // PRIORITY 3 - ENTRY (only when flat)
   //================================================================
   if(flat)
   {
      if(dm_up)
      {
         Trade_act = 1;                        // BUY
         Trade_info += " [LAD]ENTRY_BUY";
      }
      else if(dm_down)
      {
         Trade_act = 2;                        // SELL
         Trade_info += " [LAD]ENTRY_SELL";
      }
      // dm == 3 (sideways family) or dm == 0 (warmup) -> stay flat
   }
   // In a position, same-direction dm, no sideway -> HOLD (act stays 0),
   // so the trade rides until a reversal or a sideway exit closes it.
   // This is what let DMONLY hold winners into trends.
}
