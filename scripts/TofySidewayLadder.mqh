#property copyright "Copyright 2026, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"
#property version   "39.00"
//+------------------------------------------------------------------+
//| TofySidewayLadder.mqh   -- DIAGNOSTIC ONLY                        |
//|                                                                  |
//| IT DOES NOT TRADE AND DOES NOT WRITE sideway_selected.            |
//| The existing detector and DMONLY are completely unaffected.       |
//|                                                                  |
//| ================= WHAT THE MEASUREMENTS SAY =================     |
//| Scored on 20260712_clean.log, 7603 M15 bars.                      |
//| "lift" = QUIET% of flagged bars minus the 37.8% baseline.         |
//| "window" = coverage of the 2026.02.03 12:40 - 02.04 02:05 range   |
//| (50 bars, a CHOPPY range: net 40, span 112, ER 0.035).            |
//|                                                                   |
//| EACH PREDICATE ALONE:                                             |
//|   predicate           fires   lift    window   enrichment         |
//|   A15 cluster          76%    +4.5    35/50    0.93x              |
//|   S15 stage            47%    +3.3    26/50    1.12x              |
//|   B15 dm falling       25%    +2.3     7/50    0.56x   <- DEAD     |
//|   C15 |dm| < 3         82%    +5.3    44/50    1.07x              |
//|   W15 dbbw < 1         52%    +4.8    30/50    1.15x              |
//|   A30 cluster          62%    +5.4    33/50    1.07x              |
//|   S30 stage            49%    +4.1    34/50    1.40x              |
//|   B30 dm falling       25%    +1.2    17/50    1.37x   <- DEAD     |
//|   C30 |dm| < 1.5       41%   +10.9    11/50    0.54x   <- STRONGEST|
//|   W30 dbbw < 1         49%    +4.4    31/50    1.26x              |
//|                                                                   |
//| B15 and B30 are REMOVED - they measured +2.3 and +1.2, and B15     |
//| fires LESS often inside the target window than chance (0.56x).     |
//| Dropping them changed lift by +0.1, i.e. they contributed nothing. |
//|                                                                   |
//| C30 alone scores +10.9 - more than the whole original ladder.      |
//| Most of this module's value comes from that single condition.      |
//|                                                                   |
//| PROFILES (all with breakout cancel mode 1, CL_NEAR 10.5):          |
//|   0 BALANCED   n=3158 (42%)  lift +11.2  window 25/50  enrich 1.20x|
//|   1 PRECISION  n=2701 (35%)  lift +13.3  window 19/50  enrich 1.07x|
//|   2 MINIMAL    n=2384 (31%)  lift +14.7  window 11/50  enrich 0.70x|
//|   (for reference: TofySideway n=1681 (22%) lift +16.1 window 6/50) |
//|                                                                   |
//| PRECISION AND WINDOW COVERAGE PULL IN OPPOSITE DIRECTIONS.         |
//| The target range is CHOPPY; optimising aggregate lift pushes the   |
//| detector toward QUIET periods, which is not the same thing.        |
//| Profile 0 has the best enrichment (1.20x) - it carries the most    |
//| information about the range per bar flagged - so it is the default.|
//| ==============================================================     |
//|                                                                   |
//| FIELD NAMES: BBW_stage, BB_midline_Cluster and BBMidLV are         |
//| confirmed from existing code. BB_diffMid, BB_diffBBW, BBUppLV and  |
//| BBLowLV are INFERRED from the log fields - substitute the real     |
//| member names if the compiler rejects them.                        |
//+------------------------------------------------------------------+

//--- profile: 0 = BALANCED (default), 1 = PRECISION, 2 = MINIMAL
int    SL_Profile   = 0;

//--- display
bool   SL_Draw      = true;
bool   SL_ShowFails = true;     // draw gray L0 labels for undetected bars
bool   SL_WriteLog  = true;
int    SL_FontSize  = 10;
double SL_Angle     = 90.0;     // OBJPROP_ANGLE is a DOUBLE property

//--- thresholds
double CL_NEAR        = 10.5;   // 10.0 rejected clus = 10.1 by 0.1 and broke the chain
double SL_diffmid_m15 = 3.0;    // C15
double SL_diffmid_m30 = 1.5;    // C30 - the strongest single predicate
double SL_diffbbw_m15 = 1.0;    // W15 (unused: M15 side is saturated)
double SL_diffbbw_m30 = 1.0;    // W30

//--- breakout cancel: 0 off, 1 raw (best lift), 2 two bars, 3 raw AND !C15
//---   0  n=3756 (49%) lift  +8.4   flips   0
//---   1  n=2891 (38%) lift +12.1   flips 887   <- default, most precise
//---   2  n=3423 (45%) lift  +9.5   flips 406
//---   3  n=3657 (48%) lift  +9.4   flips 172   <- steadiest
//--- Flicker is cosmetic while this module drives nothing.
int    SL_BreakoutMode = 3;

//--- H1 level: measured +3.2 vs +10.2 for level 2. Kept off.
bool   SL_UseH1     = false;

//--- ladder state history: [LA] = current, ages toward [LA_4]
int SL_state[5];

//+------------------------------------------------------------------+
bool SL_StageOK(int st)
{  return (st == 512 || st == 523 || (st >= 400 && st <= 499)); }

//+------------------------------------------------------------------+
//| Call ONCE per M15 bar, AFTER BBDatas_Midline_Cluster has run.    |
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

   //--- inputs -----------------------------------------------------
   double c0  = BBTFImpact.BB_midline_Cluster[0][LA];    // |M15 - M5|
   double c0a = BBTFImpact.BB_midline_Cluster[0][LA_1];
   double c0b = BBTFImpact.BB_midline_Cluster[0][LA_2];
   double c1  = BBTFImpact.BB_midline_Cluster[1][LA];    // |M15 - M30|
   double c1a = BBTFImpact.BB_midline_Cluster[1][LA_1];
   double c1b = BBTFImpact.BB_midline_Cluster[1][LA_2];

   double dm1  = MathAbs(BB_datas[1].BB_diffMid[LA]);
   double dm1a = MathAbs(BB_datas[1].BB_diffMid[LA_1]);
   double dm2  = MathAbs(BB_datas[2].BB_diffMid[LA]);
   double dm2a = MathAbs(BB_datas[2].BB_diffMid[LA_1]);

   double dw2  = BB_datas[2].BB_diffBBW[LA];
   double dw2a = BB_datas[2].BB_diffBBW[LA_1];

   //--- predicates -------------------------------------------------
   //--- M15: is the fast timeframe settled?
   bool A15 = ((c0 < c0a && c0a < c0b) || (c0 < CL_NEAR && c0a < CL_NEAR));  // +4.5
   bool S15 = SL_StageOK((int)BB_datas[1].BBW_stage[LA]);                    // +3.3
   bool C15 = (dm1 < SL_diffmid_m15 && dm1a < SL_diffmid_m15);               // +5.3

   //--- M30: is the slower timeframe settled?
   bool A30 = ((c1 < c1a && c1a < c1b) || (c1 < CL_NEAR && c1a < CL_NEAR));  // +5.4
   bool S30 = SL_StageOK((int)BB_datas[2].BBW_stage[LA]);                    // +4.1
   bool C30 = (dm2 < SL_diffmid_m30 && dm2a < SL_diffmid_m30);               // +10.9
   bool W30 = (dw2 < SL_diffbbw_m30 && dw2a < SL_diffbbw_m30);               // +4.4

   //--- LEVEL 1: M15 settled ---------------------------------------
   bool lvl1 = (A15 && (S15 || C15));
   if(lvl1) SL_state[LA] = 1;

   //--- LEVEL 2: M30 confirms, and the chain must already be running
   //--- prev >= 1 (not == 1) lets the state PERSIST. With == 1 a bar at
   //--- level 2 could never re-qualify and the state collapsed every bar;
   //--- that fix alone took coverage from 1019 to 2648 bars.
   bool lvl2 = false;
   if(prev >= 1 && A30)
   {
      if(SL_Profile == 2)      lvl2 = C30;                  // MINIMAL
      else if(SL_Profile == 1) lvl2 = (S30 || C30);         // PRECISION
      else                     lvl2 = (S30 || C30 || W30);  // BALANCED
   }
   if(lvl2) SL_state[LA] = 2;

   //--- BREAKOUT CANCELS the state (M15 band, index 1) --------------
   //--- M15 beat M30 (+12.1 vs +9.8) and beat every sequential variant.
   //--- M15 bands are tighter: they break earlier AND re-contain earlier.
   bool brk = false;
   if(SL_BreakoutMode > 0)
   {
      double close_now  = iClose(_Symbol, PERIOD_M5, 0);
      double close_prev = iClose(_Symbol, PERIOD_M5, 3);   // 3 M5 bars = 1 M15 bar

      bool raw  = (close_now  > BB_datas[1].BBUppLV[LA]
                || close_now  < BB_datas[1].BBLowLV[LA]);
      bool raw1 = (close_prev > BB_datas[1].BBUppLV[LA_1]
                || close_prev < BB_datas[1].BBLowLV[LA_1]);

      if(SL_BreakoutMode == 1)      brk = raw;
      else if(SL_BreakoutMode == 2) brk = (raw && raw1);
      else if(SL_BreakoutMode == 3) brk = (raw && !C15);

      if(brk) SL_state[LA] = 0;
   }

   //--- LEVEL 3: H1. Measured +3.2 vs +10.2 for level 2. Off by default.
   if(SL_UseH1 && prev >= 2 && !brk)
   {
      double c2  = BBTFImpact.BB_midline_Cluster[2][LA];
      double c2a = BBTFImpact.BB_midline_Cluster[2][LA_1];
      double c2b = BBTFImpact.BB_midline_Cluster[2][LA_2];
      bool A1H = ( SL_StageOK((int)BB_datas[3].BBW_stage[LA])
                || (BB_datas[3].BB_diffBBW[LA]   < BB_datas[3].BB_diffBBW[LA_1]
                 && BB_datas[3].BB_diffBBW[LA_1] < BB_datas[3].BB_diffBBW[LA_2]) );
      bool B1H = (c2 < c2a && c2a < c2b);
      bool C1H = (c1 < CL_NEAR && c1a < CL_NEAR);
      if(A1H && B1H && C1H) SL_state[LA] = 3;
   }

   //--- why did it not go higher? report the gate for the level REACHED
   string why = "";
   if(SL_state[LA] == 0)
   {
      if(brk)       why = "brk";
      else if(!A15) why = "A15";
      else          why = "SC15";      // neither S15 nor C15
   }
   else if(SL_state[LA] == 1)
   {
      if(prev < 1)  why = "prev";      // chain not running yet
      else if(!A30) why = "A30";
      else          why = "SCW30";     // M30 evidence gates all failed
   }

   //--- draw -------------------------------------------------------
   if(SL_Draw)
   {
      double mid = BB_datas[1].BBMidLV[LA];
      datetime t = iTime(_Symbol, PERIOD_M15, 0);

      if(mid > 0.0 && t > 0 && (SL_state[LA] > 0 || SL_ShowFails))
      {
         string txt = "L" + IntegerToString(SL_state[LA]);
         if(why != "") txt += "-" + why;

         string name = txt + "_" + IntegerToString((int)t);   // ID only: one label per bar
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

   //--- log --------------------------------------------------------
   if(SL_WriteLog)
   {
      Print("[LADDER] state:[", SL_state[LA],
            "] prev:[", prev,
            "] why:[", why,
            "] prof:[", SL_Profile,
            "] A15:[", A15, "] S15:[", S15, "] C15:[", C15,
            "] A30:[", A30, "] S30:[", S30, "] C30:[", C30, "] W30:[", W30,
            "] brk:[", brk, "] brkmode:[", SL_BreakoutMode,
            "] c0:[", DoubleToString(c0,1),
            "] c1:[", DoubleToString(c1,1),
            "] ws15:[", (int)BB_datas[1].BBW_stage[LA],
            "] ws30:[", (int)BB_datas[2].BBW_stage[LA], "]");
   }
}
