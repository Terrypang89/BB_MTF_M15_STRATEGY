#property copyright "Copyright 2024, terrypang."
#property link      "https://www.mql5.com/en/users/terrypang/"

#include <TofyIncludeSimple.mqh>

//+------------------------------------------------------------------+
//| Midline-cluster distance thresholds (price units).                |
//| BB_midline_Cluster[0] = |M15 mid - M5  mid|                       |
//| BB_midline_Cluster[1] = |M15 mid - M30 mid|                       |
//| BB_midline_Cluster[2] = |M15 mid - H1  mid|                       |
//+------------------------------------------------------------------+
const double CLUS_VTIGHT = 3.0;    // was 3   (S_51)
const double CLUS_TIGHT  = 6.0;    // was 6   (S_11/12/13, S_21..24, S_41)
const double CLUS_MED    = 10.0;   // was 10  (S_11/12/13, S_31/32, S_41)
const double CLUS_LOOSE  = 15.0;   // was 15  (S_31/32)
//+------------------------------------------------------------------+

//--- cluster label display (diagnostic only; safe to read - no lookahead)
bool   DC_Draw     = true;
int    DC_FontSize = 9;
double DC_Angle    = 90.0;   // 0.0 for horizontal
int    DC_Digits   = 1;
//+------------------------------------------------------------------+

void BBDatas_Midline_Cluster(BB_MTF_Impact_struct &BBTFImpact, BB_MTF_Data_struct &BB_datas[])
{
   double tempval[3], maxMid[3], minMid[3];
   
   double m5Mid = BB_datas[0].BBMidLV[LA];
   double m15Mid = BB_datas[1].BBMidLV[LA];
   double m30Mid = BB_datas[2].BBMidLV[LA];
   double h1Mid  = BB_datas[3].BBMidLV[LA];

   // M15 vs M5
   maxMid[0] = MathMax(m15Mid, m5Mid);
   minMid[0] = MathMin(m15Mid, m5Mid);

   // M15 vs M30
   maxMid[1] = MathMax(m15Mid, m30Mid);
   minMid[1] = MathMin(m15Mid, m30Mid);

   maxMid[2] = MathMax(m15Mid, h1Mid);
   minMid[2] = MathMin(m15Mid, h1Mid);

   maxMid[3] = MathMax(m30Mid, h1Mid);
   minMid[3] = MathMin(m30Mid, h1Mid);

   for(int i = 0; i < 4; i++)
   {
      tempval[i] = (maxMid[i] - minMid[i]);
      if(tempval[i] != BBTFImpact.BB_midline_Cluster[i][LA])
      {
         BBTFImpact.BB_midline_Cluster[i][LA_4] = BBTFImpact.BB_midline_Cluster[i][LA_3];
         BBTFImpact.BB_midline_Cluster[i][LA_3] = BBTFImpact.BB_midline_Cluster[i][LA_2];
         BBTFImpact.BB_midline_Cluster[i][LA_2] = BBTFImpact.BB_midline_Cluster[i][LA_1];
         BBTFImpact.BB_midline_Cluster[i][LA_1] = BBTFImpact.BB_midline_Cluster[i][LA];
         BBTFImpact.BB_midline_Cluster[i][LA] = tempval[i];
      }
   }
}

//+------------------------------------------------------------------+
//| Draw the three midline-cluster distances on the M15 midline.      |
//|   c 3.2|10.8|15.5   =  M15-M5 | M15-M30 | M15-H1                  |
//| Smaller = midlines bunched = timeframes agree.                    |
//| Colour = which gate tier Cluster[0] falls into (it appears in 6  |
//| of the 13 threshold tests below).                                 |
//| NO LOOKAHEAD - current-bar values only.                           |
//+------------------------------------------------------------------+
void DC_DrawClusterLabel(BB_MTF_Impact_struct &BBTFImpact,
                         BB_MTF_Data_struct &BB_datas[])
{
   if(!DC_Draw) return;

   double mid_M15 = BB_datas[1].BBMidLV[LA];      // index 1 = M15
   if(mid_M15 <= 0.0) return;

   datetime t_bar = iTime(_Symbol, PERIOD_M15, 0);
   if(t_bar <= 0) return;

   // keep the DOUBLES for the gate comparison
   double c0 = BBTFImpact.BB_midline_Cluster[0][LA];
   double c1 = BBTFImpact.BB_midline_Cluster[1][LA];
   double c2 = BBTFImpact.BB_midline_Cluster[2][LA];

   // truncate ONLY for display
   string txt = IntegerToString((int)c0)
              + "-" + IntegerToString((int)c1)
              + "-" + IntegerToString((int)c2);

   string name = txt + "_" + IntegerToString((int)t_bar);   // timestamp only = one per bar
   if(ObjectFind(0, name) >= 0) return;

   color col;
   if(c0 <= CLUS_VTIGHT)     col = clrLime;      // compares the DOUBLE
   else if(c0 <= CLUS_TIGHT) col = clrAqua;
   else if(c0 <= CLUS_MED)   col = clrYellow;
   else                      col = clrGray;

   if(!ObjectCreate(0, name, OBJ_TEXT, 0, t_bar, mid_M15)) return;
   ObjectSetString (0, name, OBJPROP_TEXT,     txt);
   ObjectSetInteger(0, name, OBJPROP_COLOR,    col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, DC_FontSize);
   ObjectSetDouble (0, name, OBJPROP_ANGLE,    DC_Angle);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_LOWER);
   ObjectSetInteger(0, name, OBJPROP_BACK,     false);
}

void BBDatas_Midline_Sideway(BB_MTF_Impact_struct &BBTFImpact, BB_MTF_Data_struct &BB_datas[])
{

   BBTFImpact.sideway_selected[LA_4] = BBTFImpact.sideway_selected[LA_3];
   BBTFImpact.sideway_selected[LA_3] = BBTFImpact.sideway_selected[LA_2];
   BBTFImpact.sideway_selected[LA_2] = BBTFImpact.sideway_selected[LA_1];
   BBTFImpact.sideway_selected[LA_1] = BBTFImpact.sideway_selected[LA];
   BBTFImpact.sideway_selected[LA] = 0;
   for(int i=4; i>= 0; i--)
   {
      BBTFImpact.sideway_val[i] = 0; 
      if(BB_datas[i].BB_diffMid_Trend[LA] >= 3)
      {
         BBTFImpact.sideway_val[i] += 4;
      }
      if(BB_datas[i].BBW_stage[LA] < 500)
      {
         BBTFImpact.sideway_val[i] += 2;
      }
      else if((BB_datas[i].BBW_stage[LA] == 513 || BB_datas[i].BBW_stage[LA] == 523))
      {
         BBTFImpact.sideway_val[i] += 1;
      }
   }

  
   // when M5 + M15 cluster and M15 + M30 cluster or when M5 + M15 cluster and M15 + H1 cluster
   if((BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_MED) || \
      (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[2][LA] <= CLUS_MED))
   {
      // M5 fly_shrink or above & M15 diffmid_trend sideway or stage sideway 
      if(BBTFImpact.sideway_val[0] >= 1 && BBTFImpact.sideway_val[1] >= 4 && (BBTFImpact.sideway_val[3] >= 2 || BBTFImpact.sideway_val[2] >= 4))
      {
         BBTFImpact.sideway_selected[LA] = 11;
      }
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 1 && (BBTFImpact.sideway_val[3] >= 2 || BBTFImpact.sideway_val[2] >= 4))
      {
         BBTFImpact.sideway_selected[LA] = 12;
      }
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[LA] = 13;
      }
   }
   // M15 + M5 cluster only
   if(BBTFImpact.sideway_selected[LA] == 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[0][LA_1] <= CLUS_TIGHT))
   {
      // M5 diffmid_trend sideway, M5 BBW_stage sideway
      if(BBTFImpact.sideway_val[0] >= 6)
      {
         BBTFImpact.sideway_selected[LA] = 21;
      }
      // M5 diffmid_trend sideway & M15 BBW_stage sideway or diffmid_trend sideway
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[LA] = 22;
      }
      else if(BBTFImpact.sideway_val[1] >= 2 && BBTFImpact.sideway_val[3] >= 5)
      {
         BBTFImpact.sideway_selected[LA] = 23;
      }
      // 
      else if(BBTFImpact.sideway_val[0] >= 5 && BBTFImpact.sideway_val[1] >= 1)
      {
         BBTFImpact.sideway_selected[LA] = 24;
      }
   }

   //  M5 + M15 cluster, M15 + M30 cluster
   if(BBTFImpact.sideway_selected[LA] == 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_MED && BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_LOOSE))
   {
      // M5 diffmid_trend sideway,  
      // during M30 && H1 fly, M5 start fly_shrink
      if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[LA] = 31;
      }
      else if(BBTFImpact.sideway_val[1] >= 2 && BBTFImpact.sideway_val[3] >= 5)
      {
         BBTFImpact.sideway_selected[LA] = 32;
      }
   }
   // check if prev is sideway and M30 or H1 still sideway
   if(BBTFImpact.sideway_selected[LA] == 0 && BBTFImpact.sideway_selected[1] != 0 && BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[2][LA] <= CLUS_MED)
   {
      // M30 stage sideway or diffmidtrend sideway / H1 stage sideway or diffmidtrend sideway & H4 stage sideway or diffmidtrend sideway
      if((BBTFImpact.sideway_val[0] >= 1 || BBTFImpact.sideway_val[1] >= 1) && (BBTFImpact.sideway_val[2] >= 2) && (BBTFImpact.sideway_val[3] >= 2) && (BBTFImpact.sideway_val[4] >= 2))
      {
         BBTFImpact.sideway_selected[LA] = 41;
      }
   }
   // if prev is sideway, 
   if(BBTFImpact.sideway_selected[LA] == 0 && BBTFImpact.sideway_selected[1] != 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_VTIGHT || BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_VTIGHT) && \
      (BBTFImpact.BB_midline_Cluster[0][LA] < BBTFImpact.BB_midline_Cluster[0][LA_1] || BBTFImpact.BB_midline_Cluster[1][LA] < BBTFImpact.BB_midline_Cluster[1][LA_1]))
   {
      if(BBTFImpact.sideway_val[1] >= 6)
      {
         BBTFImpact.sideway_selected[LA] = 51;
      }
   }
   DC_DrawClusterLabel(BBTFImpact, BB_datas);
}