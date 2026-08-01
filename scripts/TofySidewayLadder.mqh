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
int    SL_FontSize  = 9;
double SL_Angle     = 90.0;     // OBJPROP_ANGLE is a DOUBLE property
double CL_NEAR      = 10.0;     // the "< 10" cluster gate
bool   SL_UseH1     = false;    // measured to DEGRADE the ladder; off by default

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

   //--- M15 block -> state 1
   bool A15 = ((c0 < c0a && c0a < c0b) || (c0 < CL_NEAR && c0a < CL_NEAR));
   bool B15 = ( SL_StageOK((int)BB_datas[1].BBW_stage[LA])
             || (BB_datas[1].BB_diffMid[LA] < BB_datas[1].BB_diffMid[LA_1]
              && BB_datas[1].BB_diffMid[LA_1] < BB_datas[1].BB_diffMid[LA_2]) );
   if(A15 && B15) SL_state[LA] = 1;

   //--- M30 block -> state 2 (needs previous bar == 1)
   bool A30 = ((c1 < c1a && c1a < c1b) || (c1 < CL_NEAR && c1a < CL_NEAR));
   bool B30 = ( SL_StageOK((int)BB_datas[2].BBW_stage[LA])
             || (BB_datas[2].BB_diffMid[LA] < BB_datas[2].BB_diffMid[LA_1]
              && BB_datas[2].BB_diffMid[LA_1] < BB_datas[2].BB_diffMid[LA_2]) );
   if(prev == 1 && A30 && B30) SL_state[LA] = 2;

   //--- H1 block -> state 3 (needs previous bar == 2). OFF by default.
   bool A1H = false, B1H = false, C1H = false;
   if(SL_UseH1)
   {
      A1H = ( SL_StageOK((int)BB_datas[3].BBW_stage[LA])
           || (BB_datas[3].BB_diffBBW[LA] < BB_datas[3].BB_diffBBW[LA_1]
            && BB_datas[3].BB_diffBBW[LA_1] < BB_datas[3].BB_diffBBW[LA_2]) );
      B1H = (c2 < c2a && c2a < c2b);
      C1H = (c1 < CL_NEAR && c1a < CL_NEAR);
      if(prev == 2 && A1H && B1H && C1H) SL_state[LA] = 3;
   }

   //--- why did it fail? (for the label and log)
   string why = "";
   if(SL_state[LA] == 0)
   {
      if(!A15) why += "A";      // cluster gate failed
      if(!B15) why += "B";      // stage / diffMid gate failed
      if(why == "") why = "P";  // blocks passed but prev level not met
   }

   //--- draw
   if(SL_Draw)
   {
      double mid = BB_datas[1].BBMidLV[LA];
      datetime t = iTime(_Symbol, PERIOD_M15, 0);
      if(mid > 0.0 && t > 0)
      {
         string name = "SL_" + IntegerToString((int)t);
         if(ObjectFind(0, name) < 0)
         {
            string txt = "L" + IntegerToString(SL_state[LA]);
            if(SL_state[LA] == 0) txt += "-" + why;

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
            "] A15:[", A15, "] B15:[", B15,
            "] A30:[", A30, "] B30:[", B30,
            "] c0:[", DoubleToString(c0,1),
            "] c1:[", DoubleToString(c1,1),
            "] c2:[", DoubleToString(c2,1),
            "] ws15:[", (int)BB_datas[1].BBW_stage[LA],
            "] ws30:[", (int)BB_datas[2].BBW_stage[LA], "]");
   }
}
