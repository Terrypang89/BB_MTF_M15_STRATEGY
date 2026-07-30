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

   for(int i = 0; i < 3; i++)
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

void BBDatas_Midline_Sideway(BB_MTF_Impact_struct &BBTFImpact, BB_MTF_Data_struct &BB_datas[])
{

   BBTFImpact.sideway_selected[4] = BBTFImpact.sideway_selected[3];
   BBTFImpact.sideway_selected[3] = BBTFImpact.sideway_selected[2];
   BBTFImpact.sideway_selected[2] = BBTFImpact.sideway_selected[1];
   BBTFImpact.sideway_selected[1] = BBTFImpact.sideway_selected[0];
   BBTFImpact.sideway_selected[0] = 0;
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
         BBTFImpact.sideway_selected[0] = 11;
      }
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 1 && (BBTFImpact.sideway_val[3] >= 2 || BBTFImpact.sideway_val[2] >= 4))
      {
         BBTFImpact.sideway_selected[0] = 12;
      }
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[0] = 13;
      }
   }
   // M15 + M5 cluster only
   if(BBTFImpact.sideway_selected[0] == 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[0][LA_1] <= CLUS_TIGHT))
   {
      // M5 diffmid_trend sideway, M5 BBW_stage sideway
      if(BBTFImpact.sideway_val[0] >= 6)
      {
         BBTFImpact.sideway_selected[0] = 21;
      }
      // M5 diffmid_trend sideway & M15 BBW_stage sideway or diffmid_trend sideway
      else if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[0] = 22;
      }
      else if(BBTFImpact.sideway_val[1] >= 2 && BBTFImpact.sideway_val[3] >= 5)
      {
         BBTFImpact.sideway_selected[0] = 23;
      }
      // 
      else if(BBTFImpact.sideway_val[0] >= 5 && BBTFImpact.sideway_val[1] >= 1)
      {
         BBTFImpact.sideway_selected[0] = 24;
      }
   }

   //  M5 + M15 cluster, M15 + M30 cluster
   if(BBTFImpact.sideway_selected[0] == 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_MED && BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_LOOSE))
   {
      // M5 diffmid_trend sideway,  
      // during M30 && H1 fly, M5 start fly_shrink
      if(BBTFImpact.sideway_val[0] >= 4 && BBTFImpact.sideway_val[1] >= 2)
      {
         BBTFImpact.sideway_selected[0] = 31;
      }
      else if(BBTFImpact.sideway_val[1] >= 2 && BBTFImpact.sideway_val[3] >= 5)
      {
         BBTFImpact.sideway_selected[0] = 32;
      }
   }
   // check if prev is sideway and M30 or H1 still sideway
   if(BBTFImpact.sideway_selected[0] == 0 && BBTFImpact.sideway_selected[1] != 0 && BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_TIGHT && BBTFImpact.BB_midline_Cluster[2][LA] <= CLUS_MED)
   {
      // M30 stage sideway or diffmidtrend sideway / H1 stage sideway or diffmidtrend sideway & H4 stage sideway or diffmidtrend sideway
      if((BBTFImpact.sideway_val[0] >= 1 || BBTFImpact.sideway_val[1] >= 1) && (BBTFImpact.sideway_val[2] >= 2) && (BBTFImpact.sideway_val[3] >= 2) && (BBTFImpact.sideway_val[4] >= 2))
      {
         BBTFImpact.sideway_selected[0] = 41;
      }
   }
   // if prev is sideway, 
   if(BBTFImpact.sideway_selected[0] == 0 && BBTFImpact.sideway_selected[1] != 0 && (BBTFImpact.BB_midline_Cluster[0][LA] <= CLUS_VTIGHT || BBTFImpact.BB_midline_Cluster[1][LA] <= CLUS_VTIGHT) && \
      (BBTFImpact.BB_midline_Cluster[0][LA] < BBTFImpact.BB_midline_Cluster[0][LA_1] || BBTFImpact.BB_midline_Cluster[1][LA] < BBTFImpact.BB_midline_Cluster[1][LA_1]))
   {
      if(BBTFImpact.sideway_val[1] >= 6)
      {
         BBTFImpact.sideway_selected[0] = 51;
      }
   }
}