#cd A2EI_PY/AAM_APP & streamlit run MA_FC_AAM_APP.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, time , timedelta
from matplotlib.dates import DateFormatter
from plotly.subplots import make_subplots
import streamlit as st
import time
import math #for status
from sqlalchemy import *
import csv
import glob
from pathlib import Path


st.set_page_config(
     page_title="MA_FC_AAM App",
     page_icon=":sunny:",
     initial_sidebar_state="expanded",
     layout="wide",)

st.markdown("<h1 style='text-align: center; color: rgb(223,116,149);'>AMM DATA TOOL</h1>", unsafe_allow_html=True)


#Set 
today= time.strftime("%Y_%m_%d_")#Today's date
aam_name= str(st.sidebar.selectbox('Select AAM Name', ['206','283','316','376','511','524','527','528','557','563','576','602','645','654','661','663','691','698','937','943','945','1076','1167']))#Set System Name



gen_consump= float(2)#liter/kwh

co2_fuel=float(2.64)#kgco2/liter

usd_fuel=float( 0.4)#USD/liter
        



#path2merges= "C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/use_data/use_"+aam_name+".csv"#Set Path for merges 
#path2locations= "C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/locations.csv" 

path2merges= "use_data/use_"+aam_name+".csv"#Set Path for merges 
path2locations= "locations.csv" 

wa_bot_use = pd.read_csv("wa_bot_use.csv",
                        parse_dates=['log_date'],
                        index_col=['log_date'])#set Timestamp column as index

wa_bot_current= wa_bot_use.loc[wa_bot_use['aam_id'] == int(aam_name) ]

#Set time from where Merge should start
time_start=st.sidebar.date_input('Time start',value=(datetime(2021, 8, 1)))
time_end=st.sidebar.date_input('Time end',value=(datetime(2021, 9, 30)))

#import data set
system_data_all = pd.read_csv(path2merges ,parse_dates=['UTC'],index_col=['UTC'])## Import Data from the merge
system_data_all.sort_index(inplace=True)


system_data_time = system_data_all[time_start : time_end]

#import aam system information 
#aam_main=pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/aam_main.csv")#,index_col='aam_name')
aam_main=pd.read_csv("aam_main.csv")

aam_main_sidebar= aam_main.loc[ aam_main['aam_name'] == int(aam_name) ]
bat_size= aam_main_sidebar['bat_size'].iloc[0].astype(str) 
pv_location= aam_main_sidebar['location_solar_radiation'].iloc[0]
aam_main_sidebar= aam_main_sidebar.astype(str) 
st.sidebar.header('Overview System: '+aam_name)
st.sidebar.table(aam_main_sidebar.T)

solar_radiation = pd.read_csv("pv_data_2005_2016.csv",
                                 sep=',',
                                parse_dates=['Month'],
                                index_col=['Month'])#set Timestamp column as index

solar_radiation['month'] = pd.DatetimeIndex(solar_radiation.index).month
#solar_radiation_m.to_datetime('Month', format='%m')
solar_radiation_m=pd.DataFrame(columns=[])
solar_radiation_m[pv_location]=solar_radiation[pv_location].resample('M').sum()
dates = pd.date_range('2021-01-01', '2021-12-31', freq='D')

solar_radiation_d=pd.DataFrame(columns=[])                               
solar_radiation_d[pv_location]= solar_radiation[pv_location].reindex(dates, method='ffill')
solar_radiation_d[pv_location]= solar_radiation_d[pv_location]/solar_radiation_d.index.daysinmonth

## Separate data into Inverter, MPPT and MCU Data

## Data Processing

#create new usefull columns
system_data_time['output_load'] = system_data_time['output_current_inv']*system_data_time['battery_voltage_inv']
system_data_time['aam_off_time']= 0
system_data_time['aam_off_time'].mask(np.isnan(system_data_time['temperature_inv']),5,inplace=True)
system_data_time['aam_on_time']= 0
system_data_time['aam_on_time'].mask(system_data_time['temperature_inv']>=0,5, inplace=True)

system_data_time['PV_W']=0
system_data_time['PV_W']= system_data_time['mppt_output_voltage']*system_data_time['mppt_output_current']
system_data_time['PV_W_on']=0
system_data_time['PV_W_on'].mask(system_data_time['PV_W']!=0,system_data_time['PV_W'],inplace=True) #takes out the 0V data points 
system_data_time['PV_E_Wh']=system_data_time['PV_W']*(5/60)

#Analize Load 
df_load=pd.DataFrame(columns=['load_wh','load_wh_grid','load_wh_pv','load_wh_bat','PV_W','output_load','input_voltage','output_load_on'])

#import columns from different components
df_load['PV_W']=system_data_time['PV_W']
df_load['E_Wh']=system_data_time['PV_E_Wh']
df_load['output_load']=system_data_time['output_load']
df_load['output_load_on'].mask(df_load['output_load']!=0,df_load['output_load'],inplace=True) #takes out the 0W data points for plot
df_load['input_voltage_inv']=system_data_time['input_voltage_inv']
df_load['load_wh']=df_load['output_load']*(5/60)
df_load['load_wh'].replace(np.nan,0 ,inplace=True)
df_load['load_wh_grid'].mask(df_load['input_voltage_inv']>=180,df_load['load_wh'], inplace=True)
df_load['load_wh_grid'].replace(np.nan,0 ,inplace=True)#takes out nan to be able to substract for load_wh_bat
df_load['load_wh_pv'].where((df_load['PV_W']<= df_load['output_load'])|(df_load['load_wh']==df_load['load_wh_grid']),df_load['load_wh'], inplace=True)
df_load['load_wh_pv'].where((df_load['PV_W']>= df_load['output_load'])|(df_load['load_wh']==df_load['load_wh_grid']),df_load['E_Wh'], inplace=True)
df_load['load_wh_pv'].where(df_load['PV_W']>= 20 ,0, inplace=True)
df_load['load_wh_pv'].replace(np.nan,0 ,inplace=True)
df_load['load_wh_bat']=df_load['load_wh']- df_load['load_wh_grid']-df_load['load_wh_pv']
df_load['load_wh_bat'].replace(np.nan,0 ,inplace=True)

############################################# Grid Analysis

df_grid=pd.DataFrame(columns=['input_voltage_mcu','input_voltage_mcu_shifted','input_voltage_inv','output_voltage_inv','input_voltage_mcu_not_0','input_voltage_inv_not_0','grid_avl','grid_avl_usb','grid_voltage_use','aam_avl','counter_evt','grid_on_time','grid_off_time','grid_on_time_usb','grid_off_time_usb','grid_voltage_mcu_not_0_on_time'])


df_grid['input_voltage_mcu']=system_data_time['input_voltage_mcu']
df_grid['input_voltage_mcu_shifted']=df_grid['input_voltage_mcu']
df_grid['input_voltage_mcu_not_0'].mask(df_grid['input_voltage_mcu_shifted']>0,df_grid['input_voltage_mcu_shifted'],inplace=True) #takes out the 0V data points 
df_grid['input_voltage_inv']=system_data_time['input_voltage_inv']
df_grid['input_voltage_inv_not_0'].mask(df_grid['input_voltage_inv']>0,df_grid['input_voltage_inv'],inplace=True) #takes out the 0V data points 

df_grid['output_voltage_inv'].mask(system_data_time['output_voltage_inv']>=20,system_data_time['output_voltage_inv'],inplace=True)


df_grid['grid_voltage_use'].mask((df_grid['output_voltage_inv']<=229)|(df_grid['output_voltage_inv']>=231),df_grid['input_voltage_inv'], inplace=True)
df_grid['grid_voltage_use'].replace(0,np.nan ,inplace=True)

min_amm_grid_v = round((df_grid['grid_voltage_use'].quantile(0.05)),1)

df_grid['grid_on_time_usb'].mask(df_grid['grid_voltage_use']>0,5, inplace=True)#inplace overwrite the original data frame
df_grid['grid_on_time_usb'].replace(np.nan,0 ,inplace=True) #make all nan to 0 or BL 
df_grid['grid_off_time_usb'].mask(df_grid['grid_voltage_use']==np.nan,5, inplace=True)
df_grid['grid_off_time_usb'].replace(np.nan,0 ,inplace=True) #make all nan to 0 or BL
    
#writes 5 min in the dataset when grid voltage was higher or lower than 180V 
df_grid['grid_on_time'].mask(df_grid['input_voltage_mcu']>0,5, inplace=True)#inplace overwrite the original data frame
df_grid['grid_on_time'].replace(np.nan,0 ,inplace=True) #make all nan to 0 or BL 
df_grid['grid_off_time'].mask(df_grid['input_voltage_mcu']==0,5, inplace=True)

df_grid['grid_avl'].mask(df_grid['input_voltage_mcu']>0,1,inplace=True)
df_grid['grid_avl'].mask(df_grid['input_voltage_mcu']==0,0,inplace=True)
df_grid['grid_avl']=df_grid['grid_avl'].fillna(0)#make all nan to 0 or BL 

df_grid['grid_avl_usb'].mask(df_grid['grid_voltage_use']>0,1,inplace=True)
df_grid['grid_avl_usb'].mask(df_grid['grid_voltage_use']==0,0,inplace=True)
df_grid['grid_avl_usb']=df_grid['grid_avl_usb'].fillna(0)#make all nan to 0 or BL 

#df_grid['grid_avl'].mask((df_grid['input_voltage_mcu']>=0)&(np.isnan(system_data_time['output_voltage_inv'])),1, inplace=True)
#df_grid['grid_avl'].mask((df_grid['input_voltage_mcu']>=0)|(system_data_time['output_voltage_inv']<=229),1, inplace=True)
#df_grid['grid_avl'].mask((df_grid['input_voltage_mcu']>=0)&(np.isnan(system_data_time['output_voltage_inv']))&(system_data_time['output_voltage_inv']<=229),1, inplace=True)


df_grid['grid_voltage_mcu_not_0_on_time'].mask(df_grid['input_voltage_mcu']>0,5,inplace=True) #count the minutes where grid is available doenst matter the voltage
df_grid['grid_voltage_mcu_not_0_on_time'].replace(np.nan, 0, inplace=True)



df_grid['counter_evt'] = df_grid['grid_avl'].diff().ne(0).cumsum()
df_grid['counter_bl']  = df_grid['grid_avl'].diff() 
df_grid['counter_bl']  = df_grid['counter_bl'].replace([1],0) #makes the 1 to 0 transtion back to 0 just to count BL

#Data frame counting grid events ON/OFF
df_grid_evt=pd.DataFrame(columns=[])
df_grid_evt = df_grid.groupby('counter_evt')['grid_avl'].min().to_frame(name='grid_avl').join(df_grid.groupby('counter_evt')['grid_avl'].count().rename('length'))
df_grid_evt['length_h']=df_grid_evt['length']*5/60 #lenght blackuts in hours #.mask(df_grid_evt['grid_avl']!=0)
df_grid_evt.drop(df_grid_evt.tail(2).index,inplace = True) #drop first and last row, normally this events are not complete
df_grid_evt.drop(df_grid_evt.head(2).index,inplace = True)

#Drop short events
#short_bl = df_grid_evt[ df_grid_evt['length'] <= 1 ].index
#df_grid_evt.drop(short_bl , inplace=True) #drop 5min bl

#get just grid  on events 
df_grid_evt_on=pd.DataFrame(columns=[])
df_grid_evt_on=df_grid_evt[df_grid_evt['grid_avl']==1].sort_values(by = 'length_h')

#get just on grid off events
df_grid_evt_off=pd.DataFrame(columns=[])
df_grid_evt_off=df_grid_evt[df_grid_evt['grid_avl']==0 ].sort_values(by = 'length_h')#, ascending = False)
df_grid_evt_off.reset_index(drop=True, inplace=True)
df_grid_evt_off.index = df_grid_evt_off.index + 1

#resample the 5min data to 1 hour data
hour_data= pd.DataFrame(columns=['grid_avl_h','grid_avl_h_usb','load_w_h','pv_w_h'])
hour_data['grid_avl_h']=df_grid['grid_avl'].resample('H').mean()
hour_data['grid_avl_h_usb']=df_grid['grid_avl_usb'].resample('H').mean()
hour_data['load_w_h']=df_load['output_load'].resample('H').mean()
hour_data['pv_w_h']=system_data_time['PV_W'].resample('H').mean()
hour_data['bat_v_h']=system_data_time['mppt_output_voltage'].resample('H').mean()

# Grouped hourly data to display one typical day
typ_day=pd.DataFrame(columns=['avg_grid_avl','avg_grid_avl_usb','avg_load_w','avg_pv_w','avg_bat_v'])
typ_day['avg_grid_avl']=hour_data['grid_avl_h'].groupby(hour_data.index.hour).mean()
typ_day['avg_grid_avl_std']=hour_data['grid_avl_h'].groupby(hour_data.index.hour).std()
typ_day['avg_grid_avl_usb']=hour_data['grid_avl_h_usb'].groupby(hour_data.index.hour).mean()
typ_day['avg_load_w']=hour_data['load_w_h'].groupby(hour_data.index.hour).mean()
typ_day['avg_pv_w']=hour_data['pv_w_h'].groupby(hour_data.index.hour).mean()
typ_day['avg_bat_v']=hour_data['bat_v_h'].groupby(hour_data.index.hour).mean()
typ_day.index = typ_day.index + 1
###  group also by day of year to get all the points for every hour to plot box plot
typ_day_all=pd.DataFrame(columns=['avg_grid_avl','avg_grid_avl_usb','avg_load_w','avg_pv_w','avg_bat_v'])
typ_day_all['avg_grid_avl']=df_grid['grid_avl'].groupby([df_grid.index.dayofyear.rename('day of year'),df_grid.index.hour.rename('hour')]).mean()
typ_day_all['avg_grid_avl_usb']=df_grid['grid_avl_usb'].groupby([df_grid.index.dayofyear.rename('day of year'),df_grid.index.hour.rename('hour')]).mean()
#typ_day_all=typ_day_all.reset_index(level=[0,1])#reset multiindex if necessary
typ_week=pd.DataFrame(columns=['avg_grid_avl','avg_grid_avl_usb','avg_load_w','avg_pv_w','avg_bat_v'])
typ_week['avg_grid_avl']=hour_data['grid_avl_h'].groupby((hour_data.index.dayofweek)*24+( hour_data.index.hour)).mean()
typ_week['avg_grid_avl_usb']=hour_data['grid_avl_h_usb'].groupby((hour_data.index.dayofweek)*24+( hour_data.index.hour)).mean()

#resample the 5min data to 1 day data
daily_data= pd.DataFrame(columns=['E_Wh_daily','grid_on_time_daily','grid_off_time_daily','consumption'])
daily_data['E_Wh_daily']=system_data_time['PV_E_Wh'].resample('D').sum()
daily_data['E_Wh_daily'].replace(0,np.nan ,inplace=True)
daily_data['grid_on_time_daily']=df_grid['grid_on_time'].resample('D').sum()/60
daily_data['grid_off_time_daily']=df_grid['grid_off_time'].resample('D').sum()/60
daily_data['grid_on_time_daily_usb']=df_grid['grid_on_time_usb'].resample('D').sum()/60
daily_data['grid_off_time_daily_usb']=df_grid['grid_off_time_usb'].resample('D').sum()/60
daily_data['load_wh']=df_load['load_wh'].resample('D').sum()
daily_data['load_wh'].replace(0,np.nan ,inplace=True)
daily_data['load_wh_bat']=df_load['load_wh_bat'].resample('D').sum()
daily_data['load_wh_pv']=df_load['load_wh_pv'].resample('D').sum()
daily_data['load_wh_grid']=df_load['load_wh_grid'].resample('D').sum()
daily_data['bl_daily']=abs(df_grid['counter_bl'].resample('D').sum())
daily_data['Bat_V_max']=system_data_time['mppt_output_voltage'].resample('D').max()
daily_data['Bat_V_min']=system_data_time['mppt_output_voltage'].resample('D').min()
daily_data['H(i_opt)_d']= solar_radiation_d[pv_location] #take ideal radiation 
daily_data['E_ideal']=daily_data['H(i_opt)_d']*820/1000
daily_data['PR']=daily_data['E_Wh_daily']/daily_data['E_ideal']/1000
daily_data['Yf']=daily_data['E_Wh_daily']/820
daily_data['aam_on_time_daily']=system_data_time['aam_on_time'].resample('D').sum()/60
daily_data['aam_off_time_daily']=system_data_time['aam_off_time'].resample('D').sum()/60
daily_data['co2_load']=(daily_data['load_wh_bat']+daily_data['load_wh_pv'])/1000*co2_fuel*gen_consump
daily_data['cost_savings_load']=(daily_data['load_wh_bat']+daily_data['load_wh_pv'])/1000*usd_fuel*gen_consump
daily_data['co2_pv']=(daily_data['E_Wh_daily']/1000*co2_fuel*gen_consump)
daily_data['cost_savings_pv']=(daily_data['E_Wh_daily']/1000*usd_fuel*gen_consump)


monthly_data=pd.DataFrame(columns=[])
monthly_data['bl_monthly']=abs(df_grid['counter_bl'].resample('M').sum())
monthly_data['grid_on_time_monthly']=df_grid['grid_on_time'].resample('M').sum()/60
monthly_data['grid_off_time_monthly']=df_grid['grid_off_time'].resample('M').sum()/60
monthly_data['E_KWh_m']= system_data_time['PV_E_Wh'].resample('M').sum()/1000 #sum up pv in a month
monthly_data['H(i_opt)_m']= solar_radiation_m[pv_location] #take ideal radiation 
monthly_data['E_ideal']=monthly_data['H(i_opt)_m']*820/1000
monthly_data['PR']=monthly_data['E_KWh_m']/monthly_data['E_ideal']
monthly_data['Yf']=monthly_data['E_KWh_m']/0.820

#monthly_data['PR']=daily_data['PR'].resample('M').mean()#monthly_data['E_KWh_m']/monthly_data['E_ideal']
#monthly_data['Yf']=daily_data['Yf'].resample('M').mean()#monthly_data['E_KWh_m']/0.82


#PR_aug=round(monthly_data['PR'].iloc[0],2)
#PR_sep=round(monthly_data['PR'].iloc[1],2)

#Yf_aug=round(monthly_data['Yf'].iloc[0],2)
#Yf_sep=round(monthly_data['Yf'].iloc[1],2)




##########      DAY ONLY     ##################
#Take just data on day time 
df_day= pd.DataFrame(columns=['grid_on_time_day','grid_off_time_day','aam_on_time_day','aam_off_time_day'])
df_day['grid_on_time_day']=df_grid['grid_on_time'].between_time('06:00', '18:00')
df_day['grid_off_time_day']=df_grid['grid_off_time'].between_time('06:00', '18:00')
df_day['grid_on_time_day_usb']=df_grid['grid_on_time_usb'].between_time('06:00', '18:00')
df_day['grid_off_time_day_usb']=df_grid['grid_off_time_usb'].between_time('06:00', '18:00')
df_day['aam_on_time_day']=system_data_time['aam_on_time'].between_time('06:00', '18:00')
df_day['aam_off_time_day']=system_data_time['aam_off_time'].between_time('06:00', '18:00')


#resample the day only 5 min data to day only 1 day data
daily_data_day= pd.DataFrame(columns=['grid_on_time_daily_day','grid_off_time_daily_day','aam_on_time_daily_day','aam_off_time_daily_day'])
daily_data_day['grid_on_time_daily_day']=df_day['grid_on_time_day'].resample('D').sum()/60
daily_data_day['grid_off_time_daily_day']=df_day['grid_off_time_day'].resample('D').sum()/60
daily_data_day['grid_on_time_daily_day_usb']=df_day['grid_on_time_day_usb'].resample('D').sum()/60
daily_data_day['grid_off_time_daily_day_usb']=df_day['grid_off_time_day_usb'].resample('D').sum()/60
daily_data_day['aam_on_time_daily_day']=df_day['aam_on_time_day'].resample('D').sum()/60
daily_data_day['aam_off_time_daily_day']=df_day['aam_off_time_day'].resample('D').sum()/60

##########      OPENING HOURS ONLY     ##################
#Take just data on opening hours
df_oh= pd.DataFrame(columns=['grid_on_time_oh','grid_off_time_oh','aam_on_time_oh','aam_off_time_oh'])
df_oh['grid_on_time_oh']=df_grid['grid_on_time'].between_time('06:00', '22:30')
df_oh['grid_off_time_oh']=df_grid['grid_off_time'].between_time('06:00', '22:30')
df_oh['grid_on_time_oh_usb']=df_grid['grid_on_time_usb'].between_time('06:00', '22:30')
df_oh['grid_off_time_oh_usb']=df_grid['grid_off_time_usb'].between_time('06:00', '22:30')
df_oh['aam_on_time_oh']=system_data_time['aam_on_time'].between_time('06:00', '22:30')
df_oh['aam_off_time_oh']=system_data_time['aam_off_time'].between_time('06:00', '22:30')


daily_data_oh= pd.DataFrame(columns=['grid_on_time_daily_oh','grid_off_time_daily_oh'])
daily_data_oh['grid_on_time_daily_oh']=df_oh['grid_on_time_oh'].resample('D').sum()/60
daily_data_oh['grid_off_time_daily_oh']=df_oh['grid_off_time_oh'].resample('D').sum()/60
daily_data_oh['grid_on_time_daily_oh_usb']=df_oh['grid_on_time_oh_usb'].resample('D').sum()/60
daily_data_oh['grid_off_time_daily_oh_usb']=df_oh['grid_off_time_oh_usb'].resample('D').sum()/60
daily_data_oh['aam_on_time_daily_oh']=df_oh['aam_on_time_oh'].resample('D').sum()/60
daily_data_oh['aam_off_time_daily_oh']=df_oh['aam_off_time_oh'].resample('D').sum()/60


sum_up_data=pd.DataFrame(columns=['pv_kwh','load_kwh','load_kwh_pv','load_kwh_grid','load_kwh_bat','grid_on','grid_off'])
pv_kwh=round((sum(system_data_time['PV_E_Wh'])/1000),2)
load_kwh=round((sum(df_load['load_wh'])/1000),2)
load_kwh_pv=round((sum(df_load['load_wh_pv'])/1000),2)
load_kwh_bat=round((sum(df_load['load_wh_bat'])/1000),2)
load_kwh_grid=round((sum(df_load['load_wh_grid'])/1000),2)


grid_on_all=round((sum(daily_data['grid_on_time_daily'])),1)
grid_off_all=round((sum(daily_data['grid_off_time_daily'])),1)
all_h=grid_on_all+grid_off_all

grid_on_all_usb=round((sum(daily_data['grid_on_time_daily_usb'])),1)
grid_off_all_usb=round((sum(daily_data['grid_off_time_daily_usb'])),1)
grid_useless_h=grid_on_all-grid_on_all_usb

grid_on_day=round((sum(daily_data_day['grid_on_time_daily_day'])),1)
grid_off_day=round((sum(daily_data_day['grid_off_time_daily_day'])),1)
day_h=grid_on_day+grid_off_day

grid_on_day_usb=round((sum(daily_data_day['grid_on_time_daily_day_usb'])),1)
grid_off_day_usb=round((sum(daily_data_day['grid_off_time_daily_day_usb'])),1)

grid_on_oh=round((sum(daily_data_oh['grid_on_time_daily_oh'])),1)
grid_off_oh=round((sum(daily_data_oh['grid_off_time_daily_oh'])),1)
oh_h=grid_on_oh+grid_off_oh

grid_on_oh_usb=round((sum(daily_data_oh['grid_on_time_daily_oh_usb'])),1)
grid_off_oh_usb=round((sum(daily_data_oh['grid_off_time_daily_oh_usb'])),1)

grid_avl_all=round(grid_on_all/all_h,3)
grid_avl_all_usb=round(grid_on_all_usb/all_h,3)
grid_avl_day=round(grid_on_day/day_h,3)
grid_avl_day_usb=round(grid_on_day_usb/day_h,3)
grid_avl_oh=round(grid_on_oh/oh_h,3)
grid_avl_oh_usb=round(grid_on_oh_usb/oh_h,3)

aam_on_all=round((sum(daily_data['aam_on_time_daily'])),1)
aam_off_all=round((sum(daily_data['aam_off_time_daily'])),1)
aam_all_h=aam_on_all+aam_off_all
aam_avl_all=round(aam_on_all/aam_all_h,3)

aam_on_day=round((sum(daily_data_day['aam_on_time_daily_day'])),1)
aam_off_day=round((sum(daily_data_day['aam_off_time_daily_day'])),1)
aam_day_h=aam_on_day+aam_off_day
aam_avl_day=round(aam_on_day/aam_day_h,3)

aam_on_oh=round((sum(daily_data_oh['aam_on_time_daily_oh'])),1)
aam_off_oh=round((sum(daily_data_oh['aam_off_time_daily_oh'])),1)
aam_oh_h=aam_on_oh+aam_off_oh
aam_avl_oh=round(aam_on_oh/aam_oh_h,3)

avg_bl_duration = round((df_grid_evt_off['length_h'].mean()),1)
max_bl_duration = round((df_grid_evt_off['length_h'].max()),1) 
min_bl_duration = round((df_grid_evt_off['length_h'].min()),1)

avg_grid_voltage= round((df_grid['input_voltage_mcu_not_0'].mean()),1)
min_grid_voltage= round((df_grid['input_voltage_mcu_not_0'].min()),1)
max_grid_voltage= round((df_grid['input_voltage_mcu_not_0'].max()),1)

avg_aam_voltage= round((df_grid['output_voltage_inv'].mean()),1)
min_aam_voltage= round((df_grid['output_voltage_inv'].min()),1)
max_aam_voltage= round((df_grid['output_voltage_inv'].max()),1)

avg_bl_nu_d = round((daily_data['bl_daily'].mean()),1)
min_bl_nu = round((daily_data['bl_daily'].min()),1)
max_bl_nu = round((daily_data['bl_daily'].max()),1)

avg_bl_nu_m = round((monthly_data['bl_monthly'].mean()),1)
min_bl_nu_m = round((monthly_data['bl_monthly'].min()),1)
max_bl_nu_m = round((monthly_data['bl_monthly'].max()),1)

avg_grid_daily_all= round((daily_data['grid_on_time_daily'].mean()),1)
avg_grid_daily_day= round((daily_data_day['grid_on_time_daily_day'].mean()),1)
avg_grid_daily_oh= round((daily_data_oh['grid_on_time_daily_oh'].mean()),1)

avg_load = round((df_load['output_load_on'].mean()),1)
min_load = round((df_load['output_load_on'].min()),1)
max_load = round((df_load['output_load_on'].max()),1)

#st.dataframe(daily_data['load_wh'])
avg_load_daily = round(((daily_data['load_wh']/1000).mean()),2)
min_load_daily = round((daily_data['load_wh'].min()))
max_load_daily = round((daily_data['load_wh'].max()))
sum_load_daily = round(((daily_data['load_wh']/1000).sum()))

avg_pv_daily = round(((daily_data['E_Wh_daily']/1000).mean()),2)
min_pv_daily = round(((daily_data['E_Wh_daily']/1000).min()),0)
max_pv_daily = round(((daily_data['E_Wh_daily']/1000).max()),0)

co2_load=round(((daily_data['load_wh_bat']+daily_data['load_wh_pv']).sum()/1000*co2_fuel*gen_consump),1) 
cost_savings_load=round(((daily_data['load_wh_bat']+daily_data['load_wh_pv']).sum()/1000*usd_fuel*gen_consump),1)
co2_pv= round((daily_data['E_Wh_daily'].sum()/1000*co2_fuel*gen_consump),1) 
cost_savings_pv=round((daily_data['E_Wh_daily'].sum()/1000*usd_fuel*gen_consump),1)



if bat_size=='50':
    avg_bl_bat_h=round(1853*(avg_load)**(-1.157),1)
    
if bat_size=='100':
    avg_bl_bat_h=round(4835*(avg_load)**(-1.204),1)
    

#avg_bl_bat_h
covered_bl_bat_nu =df_grid_evt_off[df_grid_evt_off['length_h'].lt(avg_bl_bat_h)].count().iloc[0]
#covered_bl_bat_nu
all_bl_nu =df_grid_evt_off.count().iloc[0]
#all_bl_nu
covered_bl_bat=covered_bl_bat_nu/all_bl_nu
#covered_bl_bat

################################################################################
#Write down some data :)

df_output = pd.read_csv("data_output.csv")#,index_col='aam_name')

df_output['avg_PR']=(df_output['PR_aug']+df_output['PR_sep'])/2

households = (df_output[df_output['aam_name'].isin(aam_main[aam_main['user_type']=='household'].aam_name)])
#households
mes = (df_output[df_output['aam_name'].isin(aam_main[aam_main['user_type']=='micro_enterprise'].aam_name)])
#mes
ongrid = (df_output[df_output['aam_name'].isin(aam_main[aam_main['connection_type']=='grid'].aam_name)])
#ongrid
active = (df_output[df_output['aam_name'].isin(aam_main[aam_main['connection_type']=='active_grid'].aam_name)])
#active
offgrid = (df_output[df_output['aam_name'].isin(aam_main[aam_main['connection_type']=='offgrid'].aam_name)])
#offgrid
gen = (df_output[df_output['aam_name'].isin(aam_main[aam_main['connection_type']=='generator'].aam_name)])
#gen
maraba = (df_output[df_output['aam_name'].isin(aam_main[aam_main['location']=='Maraba'].aam_name)])
#maraba
maraba_grid = (maraba[maraba['aam_name'].isin(aam_main[aam_main['connection_type']=='grid'].aam_name)])
#maraba_grid
bat50 = (df_output[df_output['aam_name'].isin(aam_main[aam_main['bat_size']==50].aam_name)])
bat50.reset_index(inplace=True)
avg_PR_bat50= bat50['avg_PR'].mean()
bat100 = (df_output[df_output['aam_name'].isin(aam_main[aam_main['bat_size']==100].aam_name)])
bat100.reset_index(inplace=True)
avg_PR_bat100= bat100['avg_PR'].mean()


#households=['524','563','645','654','698','937','945','1076']
#me=['206','283','316','376','511','527','528','576','602','663','691','943','1167']
#ongrid=['283','376','524','527','563','576','602','698','943','945','1076','1167']
#active=['661','528']
#offgrid=['316','557','654','663','691']
#gen=['206','645','511']
#maraba=['206','283','316','376','527','576','602','937','943','1076']


df_output['aam_name']=df_output['aam_name'].apply(str)
households['aam_name']=households['aam_name'].apply(str)
mes['aam_name']=mes['aam_name'].apply(str)
ongrid['aam_name']=ongrid['aam_name'].apply(str)
active['aam_name']=active['aam_name'].apply(str)
offgrid['aam_name']=offgrid['aam_name'].apply(str)
gen ['aam_name']=gen ['aam_name'].apply(str)
maraba['aam_name']=maraba['aam_name'].apply(str)
maraba_grid['aam_name']=maraba_grid['aam_name'].apply(str)



col1, col2 = st.columns([2,1])

df_output_current= df_output.loc[df_output['aam_name'] == str(aam_name)]
#st.metric('Grid availability', (str(round(grid_avl_all*100,1))+'%'), delta=None, delta_color='normal')
#st.metric('Grid availability', (str(round(grid_avl_all*100,1))+'%'), delta=None, delta_color='normal')

st.sidebar.dataframe(df_output_current.astype(str).T)

map_data = pd.DataFrame(aam_main_sidebar,columns=['latitude','longitude'])

if  map_data.astype(float).isnull().values.any():

    st.sidebar.warning('Location of AAM  '+ aam_name +' is unknown')

else:

    st.sidebar.map(data=map_data.astype(float), zoom=4)

if  wa_bot_current.empty :
    st.sidebar.warning('No available pictures for AAM '+ aam_name)

else :
    pic_solar=wa_bot_current.pic_solar.iloc[0]
    st.sidebar.image(pic_solar, use_column_width=True)
    
    pic_system=wa_bot_current.pic_system.iloc[0]
    st.sidebar.image(pic_system, use_column_width=True)
        
with st.expander('Plot'):
    
    #system_data_time
    col1, col2 ,col3= st.columns(3)
    col1.subheader('Inverter')
    with col1:
        battery_voltage_inv = st.checkbox('Battery Voltage',value=True)
        output_load= st.checkbox('Output Load*',value=True)
        output_voltage=st.checkbox('Output Voltage')
        output_current=st.checkbox('Output Current')
        temperature_inv=st.checkbox('Temperature Inverter')
        input_voltage=st.checkbox('Grid Voltage',value=True)
        
    with col2:
        col2.subheader('MPPT')
        mppt_w=st.checkbox('PV Power',value=True)
        pv_a=st.checkbox('PV input current')
        pv_v=st.checkbox('PV input voltage')
        mppt_v= st.checkbox('MPPT output voltage',value=True)
        mppt_a=st.checkbox('MPPT output current')
        temoerature_mppt=st.checkbox('Temperature mppt')
        temoerature_bat=st.checkbox('Temperature Battery')
        
    with col3:
        col3.subheader('MCU')
        peak_voltage=st.checkbox('Grid Voltage[V]',value=True)  
        
        st.subheader('other')
        inv_cut_off=st.checkbox('Inverter Cut Off',value=True) 
        Float=st.checkbox('Float',value=True) 
        bulk=st.checkbox('Bulk',value=True) 
        mppt_cut_off=st.checkbox('MPPT Cut OFF',value=True) 
    ########  PLOT

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    ## INVERTER
    if battery_voltage_inv:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['battery_voltage_inv'], name="Battery_Voltage_Inv",
                                line_shape='linear',line_color='coral'),secondary_y=False,)
    if output_load:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['output_load'], name="Load",
                                line_shape='linear',fill='tozeroy',mode="lines", 
                                line=dict(width=0.5, color='lightslategrey')),secondary_y=True,)#fill='tonexty' 
    
    if output_voltage:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['output_voltage_inv'], name="output_voltage",
                                line_shape='linear',mode="lines",
                                line_color='chocolate'),secondary_y=True,)
    if output_current:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['output_current_inv'], name="output_current",
                                line_shape='linear',mode="lines",
                                line_color='crimson'),secondary_y=False,) 
    
    if temperature_inv:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['temperature_inv'], name="inverter temperature",
                                line_shape='linear',mode="lines",
                                line_color='crimson'),secondary_y=False,) 
    if input_voltage:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['input_voltage_inv'], name="Grid Voltage",
                                line_shape='linear',mode="lines",
                                line_color='crimson'),secondary_y=True,) 
    
      #########  MPPT
    if mppt_w:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                 y=system_data_time['PV_W'], name="PV Power",
                                line_shape='linear',fill='tozeroy',mode="lines",
                                line=dict(width=0.5, color='gold')),secondary_y=True,)#fill='tonexty'
    if pv_a:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['pv_input_current'], name="pv_input_current",
                                line_shape='linear',mode="lines",
                                line_color='DarkOrange'),secondary_y=False,) 
    if pv_v:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['pv_input_voltage'], name="pv_input_voltage",
                                line_shape='linear',mode="lines",
                                line_color='DarkSalmon'),secondary_y=True,)     
    if mppt_v:    
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                 y=system_data_time['mppt_output_voltage'], name="mppt_output_voltage",
                                line_shape='linear',line_color='darkseagreen', mode="lines", connectgaps=False),secondary_y=False,)
    if mppt_a :  
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                 y=system_data_time['mppt_output_current'], name="mppt_output_current",
                                line_shape='linear',line_color='darkseagreen', mode="lines", connectgaps=False),secondary_y=False,)
    
    if temoerature_mppt:    
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                 y=system_data_time['temperature_mppt'], name="MPPT_Temperature",
                                line_shape='linear',line_color='red', mode="lines", connectgaps=False),secondary_y=False,)
    if temoerature_bat:    
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                 y=system_data_time['temperature_bat'], name="Battery_Temperature",
                                line_shape='linear',line_color='red', mode="lines", connectgaps=False),secondary_y=False,)

    ## ADC
    if peak_voltage:
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                y=system_data_time['input_voltage_mcu'], name="Grid_In_Voltage_ADC",
                                line_shape='linear',line_color='lightslategrey'),secondary_y=True,)

    ## Extras
    if mppt_cut_off:
        fig.add_hline(y=22.6, 
                    annotation_text="MPPT OUT 22.6",
                    line_color='dimgrey',
                    annotation_position="bottom left",
                    line_width=1,
                     line_dash='dash')
    if inv_cut_off:
        fig.add_hline(y=23.4, 
                      annotation_text="INV_CUT_OFF 23.4",
                      line_color='dimgrey',
                      annotation_position="bottom left",
                     line_width=1,
                     line_dash='dash')
    if Float:
        fig.add_hline(y=26.8, 
                      annotation_text="Float 26.8",
                      line_color='dimgrey',
                      annotation_position="bottom left",
                     line_width=1,
                     line_dash='dash')
    if bulk:
        fig.add_hline(y=28.6, 
                      annotation_text="Bulk 28.6",
                      line_color='dimgrey',
                      annotation_position="bottom left",
                    line_width=1,
                     line_dash='dash')

    fig.update_traces( mode='lines')

    fig.update_layout(
            xaxis=dict(
                showline=True,
                showgrid=True,
                showticklabels=True,
                linewidth=1.5,
                ticks='outside',
                title="Time",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                tickformat='%d/%m %H:%M', #%H:%M',
                tickfont=dict(
                    family='Fugue',
                    size=12,
                    color='rgb(82, 82, 82)'
                    ),
            ),
            yaxis=dict(
                title="Battery Voltage in V / Temperature in °C",
                showgrid=False,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                ticks='outside',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(
                    family='Fugue',
                     size=12,
                    color='rgb(82, 82, 82)',
                ),
                #range=[22,30]
            ),
            legend=dict(
                title="",
                orientation="h",
                yanchor="bottom",
                y=-0.4,
                xanchor="center",
                x=0.5,
                ),
            autosize=True,
            margin=dict(
                autoexpand=True,
                l=100,
                r=20,
                t=110,
            ),
            showlegend=True,
            plot_bgcolor='white',

            font=dict(
            family="Wigrum",
                )
            )

    fig.update_yaxes(title_text="Load in W / Grid Voltage in V", 
                         secondary_y=True,
                         ticks='outside',
                         tickfont=dict(
                                family='Fugue',
                                size=12,
                                color='rgb(82, 82, 82)',)
                         #,range=[0,600]
                         ,)
        #fig.update_layout(
         #   title_text="Battery Voltage",
          #  title_x=0.5)

    st.plotly_chart(fig, use_container_width=True)

with st.expander('Grid Analysis'):
    
    if aam_main_sidebar.connection_type.values[0] == 'active_grid':
        st.warning('This system manually activates and deactivates the grid connection')
        
    if aam_main_sidebar.connection_type.values[0] == 'generator':
        st.warning('This system uses a fuel generator')
        
    if aam_main_sidebar.connection_type.values[0] == 'offgrid':
        st.warning('This system was not connected to the grid')
        
    else:
        st.markdown("<h3 style='text-align: center'>Input and Output Voltage (AC)</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2,1])
        with col1:
            fig = go.Figure()


            #fig.add_trace(go.Scatter(x=df_grid.index, 
            #                            y=df_grid['input_voltage_mcu_shifted'], name="Input Voltage MCU",
            #                            line_shape='linear',line_color='MidnightBlue'))
#
            #fig.add_trace(go.Scatter(x=df_grid.index, 
            #                            y=df_grid['input_voltage_mcu_not_0'], name="Input Voltage MCU (no 0)",
            #                            line_shape='linear',line_color='lightslategrey'))
#
#            fig.add_trace(go.Scatter(x=df_grid.index, 
#                                        y=df_grid['grid_voltage_use'], name="Grid_Voltage_Use (MCU)",
#                                        line_shape='linear',
#                                        line = dict(color='GoldenRod', dash='dot',width=5)))


            #fig.add_trace(go.Scatter(x=df_grid.index, 
            #                            y=df_grid['input_voltage_inv'], name="Grid_In_Voltage_Inv",
            #                            line_shape='linear',line_color='MidnightBlue'))
            fig.add_trace(go.Scatter(x=df_grid.index, 
                                        y=df_grid['input_voltage_inv_not_0'], name="Grid Input Voltage Not Usable",
                                        line_shape='linear',line_color='lightslategrey',line_width=1.5))            

            fig.add_trace(go.Scatter(x=df_grid.index, 
                                        y=df_grid['grid_voltage_use'], name="Grid Input Voltage Usable",
                                        line_shape='linear',line_width=1.5,
                                        line = dict(color='GoldenRod')))
            fig.add_trace(go.Scatter(x=df_grid.index, 
                                        y=df_grid['output_voltage_inv'], name="AAM Output Voltage",
                                        line_shape='linear',line_color='rgb(223,116,149)',line_width=1.5))

            annotation_min= "Min: "+str(min_grid_voltage) +" V"
            #annotation_avg= "<b>Avg: "+str(avg_grid_voltage) +" V<b>"
            annotation_max= "Max: "+str(max_grid_voltage) +" V"
            #fig.add_hline(y=min_grid_voltage, 
            #                annotation_text= annotation_min,
            #                line_color='dimgrey',
            #                annotation_position="bottom left",
            #                line_width=1,
            #                 line_dash='dash')

            #fig.add_hline(y=avg_grid_voltage, 
            #                annotation_text= annotation_avg,
            #                line_color='dimgrey',
            #                annotation_position="bottom left",
            #                line_width=1,
            #                 line_dash='dash')

            #fig.add_hline(y=max_grid_voltage, 
            #                annotation_text= annotation_max,
            #                line_color='dimgrey',
            #                annotation_position="bottom left",
            #                line_width=1,
            #                 line_dash='dash')
            
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Time",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Grid Voltage in V",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[140,250],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="top",
                                            y=.95,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("grid_V_time_plot.pdf")
            
            
        

        #################
        with col2:
            fig = go.Figure()
            
            fig.add_trace(go.Box(y=df_grid['input_voltage_inv_not_0'],name="Grid Input Voltage All",
                                marker_color = 'lightslategrey'))
            fig.add_trace(go.Box(y=df_grid['grid_voltage_use'], name="Grid Input Voltage Usable",
                               marker_color = 'GoldenRod'))
            fig.add_trace(go.Box(y=df_grid['output_voltage_inv'],name="AAM_Output Voltage",
                                marker_color = 'rgb(223,116,149)'))
                
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=False,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Grid Voltage in V",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,300],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=True,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                                    )                                
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("grid_V_box_plot.pdf")
            
        #################################
        
       
        
        #################################
        st.markdown("<h3 style='text-align: center'>Grid and AAM Availability</h3>", unsafe_allow_html=True)
        
        select_availability  = st.radio("Time to analize availabiity",('all day', 'day light only', 'opening hours'))
        
        
        if select_availability == 'all day':
            col1, col2= st.columns([1,1])
            with col1:
                labels = ['Grid On / Usable','Grid On / Not Usable','Grid Off']
                values = [grid_on_all_usb, grid_useless_h , grid_off_all]
                colors = ['GoldenRod','lightslategrey','darkgrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent',textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="Grid Availability <br> All Day", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                 showlegend=False)
                st.plotly_chart(fig,use_container_width=True)

                #fig.write_image("grid_availability.pdf")




            with col2:
                labels = ['AAM Available','AAM Not Available']
                values = [aam_on_all, aam_off_all]
                colors = ['rgb(223,116,149)','DarkSlateGrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent', textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="AAM Availability <br> All Day", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                  #margin=dict(l=75, r=75, b=80, t=80,  pad=2),
                                 showlegend=False,
                                 )
                st.plotly_chart(fig,use_container_width=True)
                #fig.write_image("AAM_availability.pdf")
                
        if select_availability == 'day light only':
            ################################## DAY TIME
            

            col1, col2= st.columns([1,1])
            ########################################### 
            with col1:
                labels = ['Grid On / Usable','Grid On / NOT Usable','Grid Off',]
                values = [grid_on_day_usb, (grid_on_day-grid_on_day_usb), grid_off_day]
                colors = ['GoldenRod','lightslategrey','darkgrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent',textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="Grid Availability <br> Day Only", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                 showlegend=False)
                st.plotly_chart(fig,use_container_width=True)

                #fig.write_image("grid_availability_do.pdf")




            ############################################    

            with col2:
                labels = ['AAM Available','AAM Not Available']
                values = [aam_on_day, aam_off_day]
                colors = ['rgb(223,116,149)','DarkSlateGrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent', textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="AAM Availability <br> Day Only", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                  #margin=dict(l=75, r=75, b=80, t=80,  pad=2),
                                 showlegend=False,
                                 )
                st.plotly_chart(fig,use_container_width=True)
                #fig.write_image("AAM_availability_do.pdf")


        if select_availability ==  'opening hours':
            ############################################  OPENING HOURS

            col1, col2= st.columns([1,1])
            ########################################### 
            with col1:
                labels = ['Grid On / Usable','Grid On / NOT Usable','Grid Off',]
                values = [grid_on_oh_usb, (grid_on_oh-grid_on_oh_usb), grid_off_oh]
                colors = ['GoldenRod','lightslategrey','darkgrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent',textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="Grid Availability <br> Opening Hours Only", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                 showlegend=False)
                st.plotly_chart(fig,use_container_width=True)

                #fig.write_image("grid_availability_oh.pdf")



            ############################################    

            with col2:
                labels = ['AAM Available','AAM Not Available']
                values = [aam_on_oh, aam_off_oh]
                colors = ['rgb(223,116,149)','DarkSlateGrey']
                fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8 )])
                fig.update_traces(hoverinfo='label+percent', textinfo='label+percent', textfont_size=12,
                              marker=dict(colors=colors, line=dict(color='#000000', width=2)))
                fig.update_layout(annotations=[dict(text="AAM Availability <br> Opening Hours Only", x=0.5, y=0.5, font_size=12, showarrow=False)])
                fig.update_layout(font=dict( family="Fugue", size=12, color='black'),
                                 autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                  #margin=dict(l=75, r=75, b=80, t=80,  pad=2),
                                 showlegend=False,
                                 )
                st.plotly_chart(fig,use_container_width=True)
                #fig.write_image("AAM_availability_oh.pdf")




    ############# Grid Availability typical day grid avl 
        
        st.markdown("<h3 style='text-align: center'>Hourly Grid Availability Profile</h3>", unsafe_allow_html=True)
        col1, col2= st.columns([1,1])
        
        col1.subheader('All grid')
        col2.subheader('Usable grid ')
        
        
            ########################################### 
        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=typ_day.index, 
                                        y=typ_day['avg_grid_avl'], name="grid availability mean",
                                        line_shape='linear',line_color='lightslategrey',line_width=4,))

            fig.add_trace(go.Box(y=typ_day_all['avg_grid_avl'],x=typ_day_all.index.get_level_values(1)+1, marker_color = 'darkgrey',
                                    jitter=0.3,
                                    #pointpos=-1.8,
                                    #boxpoints='all',
                                            ))


            fig.update_layout(  #title='Hourly grid availability profile USB',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="hour",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[1,24],
                                    dtick = 1,
                                    ),
                                yaxis=dict(
                                    title=" Probability grid availability in %",
                                    #showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    dtick = 0.1,
                                    ticks='outside',
                                    tickformat='%',
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("hour_profile.pdf")


        with col2:
            ############# Grid Availability typical day grid avl USB

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=typ_day.index, 
                                        y=typ_day['avg_grid_avl_usb'], name="grid availability mean",
                                        line_shape='linear',line_color='GoldenRod',line_width=4,))


            fig.add_trace(go.Box(y=typ_day_all['avg_grid_avl_usb'],x=typ_day_all.index.get_level_values(1)+1, marker_color = 'darkgrey',
                                    jitter=0.3,
                                    #pointpos=-1.8,
                                    #boxpoints='all',
                                            ))
            fig.update_layout(  #title='Hourly grid availability profile USB',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="hour",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[1,24],
                                    dtick = 1,
                                    ),
                                yaxis=dict(
                                    title=" Probability grid availability in %",
                                    #showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    dtick = 0.1,
                                    ticks='outside',
                                    tickformat='%',
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("hour_profile_usb.pdf")

 
        ##################
        
        st.markdown("<h3 style='text-align: center'>Power Outage Duration</h3>", unsafe_allow_html=True)
   
        col1, col2,col3= st.columns([1,1,1])
        col1.subheader('Duration sorted by length')
        col2.subheader('Histogram ')
        col3.subheader('Distribution')
        
        with col1:
        
       
            fig = go.Figure([go.Bar(y=df_grid_evt_off['length_h'], x=df_grid_evt_off.index, 
                                    name='Blackouts per day',
                                    marker_color='lightslategrey')],)
            annotation_avg= "Avg: "+str(avg_bl_duration) +" hours"
            annotation_max= "Max: "+str(max_bl_duration) +" hours"
            annotation_min= "Min: "+str(min_bl_duration) +" hours"
            annotation_load= "Hours covered by battery: "+str(avg_bl_bat_h)+"h"
            fig.add_hline(y=avg_bl_duration, 
                                annotation_text= annotation_avg,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.add_hline(y=max_bl_duration, 
                                annotation_text= annotation_max,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.add_hline(y=min_bl_duration, 
                                annotation_text= annotation_min,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.add_hline(y=avg_bl_bat_h, 
                                annotation_text= annotation_load,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Blackout events",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title= 'Lenght of Blackout in h',
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("bl_duration_plot.pdf")
            
        
          
            
         ####################################   HISTOGRAM   ##############################################
        with col2:
            
            fig = go.Figure()

            fig.add_trace(go.Histogram(x=df_grid_evt_off['length_h'],histnorm='percent',marker_color='rgb(223,116,149)',cumulative_enabled=False,name='Histogram'))
            fig.add_trace(go.Histogram(x=df_grid_evt_off['length_h'],histnorm='percent',marker_color='lightslategrey',cumulative_enabled=True,name='Cumulative Histogram'))
                                    #name='Blackouts per day',
                                    #marker_color='DarkSeaGreen')],)
            #fig.add_vline(x=avg_bl_bat_h, 
             #                   annotation_text= annotation_load,
             #                   line_color='dimgrey',
              #                 annotation_position="bottom left",
               #                 line_width=1,
                #               line_dash='dash',)
            fig.update_traces(xbins=dict( # bins used for histogram
                                #start=0.0,
                                #end=10.0,
                                size=1),
                                autobinx = False)

            fig.update_layout(  #title_text='Histogram', # title of plot
                                xaxis_title_text='Lenght of Blackout in h', # xaxis label
                                yaxis_title_text='Percentage of Blackouts in %', # yaxis label
                                bargap=0.1, # gap between bars of adjacent location coordinates
                                #bargroupgap=0.1 # gap between bars of the same location coordinates
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="top",
                                            y=1,
                                            xanchor="left",
                                            traceorder='normal',
                                            x=0,
                                            font=dict(
                                        family="Fugue",
                                        size=12,
                                        color='black'
                                        ),
                                            ),
                                plot_bgcolor='white',
                                font=dict(
                                        family="Fugue",
                                        size=12,
                                        color='black'
                                        ),
                                xaxis=dict(
                                    range=[0,10],
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    #title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%',
                                    tick0 = 1,
                                    dtick = 1,
                                    ),
                                yaxis=dict(
                                    range=[0,110],
                                    #title=" Number of Power Outages per day",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    #tickformat='%',
                                    )
                                        #color='rgb(82, 82, 82)',),)
                            )
            st.plotly_chart(fig,use_container_width=True)
        
            #fig.write_image("Histogramm_945.pdf")
            
        with col3:      
            fig = go.Figure()
            


            fig.add_trace(go.Box(y=df_grid_evt_off['length_h'],name="length_h",
                                marker_color = 'lightslategrey'))
        
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=False,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Length of blackout in h",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,300],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=True,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                                    )                                
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("grid_V_box_plot.pdf")
        
        ##################################################################################
        st.markdown("<h3 style='text-align: center'>Power Outage Frequency</h3>", unsafe_allow_html=True)


        col1, col2, col3= st.columns([1,1,1])
        col1.subheader('Daily')
        col2.subheader('Monthly')
        col3.subheader('Distribution')
        with col1:

            fig = go.Figure([go.Bar(y=daily_data['bl_daily'], x=daily_data.index, 
                                    name='Blackouts per day',
                                    marker_color='lightslategrey')],)

            annotation_avg= "Avg: "+str(avg_bl_nu_d) +" "
            fig.add_hline(y=avg_bl_nu_d, 
                                annotation_text= annotation_avg,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            annotation_min= "Min: "+str(min_bl_nu) +" "
            fig.add_hline(y=min_bl_nu, 
                                annotation_text= annotation_min,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            annotation_max= "Max: "+str(max_bl_nu) +" "
            fig.add_hline(y=max_bl_nu, 
                                annotation_text= annotation_max,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.update_layout(  
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Number of Power Outages per day",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("bl_freq_d.pdf")
            
            
        ###############################
        with col2:

            fig = go.Figure([go.Bar(y=monthly_data['bl_monthly'], x=monthly_data.index, 
                                    name='Power Outages per month',
                                    xperiod="M1",
                                    xperiodalignment="middle",
                                    marker_color='lightslategrey')],)

            #annotation_avg= "Max: "+str(max_bl_nu_m) +" "
            #fig.add_hline(y=max_bl_nu_m, 
            #                    annotation_text= annotation_avg,
            #                    line_color='dimgrey',
            #                    annotation_position="bottom left",
            #                    line_width=1,
            #                     line_dash='dash')
            #annotation_min= "Min: "+str(min_bl_nu_m) +" "
            #fig.add_hline(y=min_bl_nu, 
            #                    annotation_text= annotation_min,
            #                    line_color='dimgrey',
            #                    annotation_position="bottom left",
            #                    line_width=1,
            #                     line_dash='dash')
            annotation_max= "AVG: "+str(avg_bl_nu_m) +" "
            fig.add_hline(y=avg_bl_nu_m, 
                                annotation_text= annotation_max,
                                line_color='dimgrey',
                                annotation_position="bottom left",
                                line_width=1,
                                 line_dash='dash')
            fig.update_layout(  
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    dtick="M1",
                                    ticklabelmode="period",
                                    tickformat="%b",
                                    #tickformat='%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Number of Power Outages per month",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             
                             
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("bl_freq_m.pdf")
            
            
            
        with col3:      
            fig = go.Figure()
            


            fig.add_trace(go.Box(y=daily_data['bl_daily'],name="bl_daily",
                                marker_color = 'lightslategrey'))
        
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=True,
                                    showticklabels=False,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Series",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black')
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title="Lenght of Blackout in h",
                                    showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,300],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=True,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                                    )                                
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("grid_V_box_plot.pdf")
with st.expander('PV Analysis'):
    
    st.markdown("<h3 style='text-align: center'>PV</h3>", unsafe_allow_html=True)
    
   
    col1, col2= st.columns([1,1])
    col1.markdown("<h3 style='text-align: center'>PV Power</h3>", unsafe_allow_html=True)
    col2.markdown("<h3 style='text-align: center'>PV Yield</h3>", unsafe_allow_html=True)
    with col1:  

            #############
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                    y=system_data_time['PV_W_on'], name="PV",
                                    line_shape='linear',line_color='gold',line_width=1))


        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Time",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,110],
                                    
                                    ),
                                yaxis=dict(
                                    title="PV Power in W",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[0,800],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                                    )          
        
        st.plotly_chart(fig, use_container_width=True)
        #fig.write_image("pv_power.pdf")

#################
    
        with col2:  
            
    
            fig = go.Figure([go.Bar(y=daily_data['E_Wh_daily']/1000, x=daily_data.index, 
                                   name='Daily PV Generation',
                                    marker_color='gold')],)
            #annotation_min= "Min: "+str(min_pv_daily/1000) +" kWh"
            annotation_avg= "Avg: "+str(avg_pv_daily) +" kWh"
            #annotation_max= "Max: "+str(max_pv_daily/1000) +" kWh"
            #fig.add_hline(y=min_pv_daily/1000, 
            #                annotation_text= annotation_min,
            #                line_color='dimgrey',
            #                annotation_position="bottom left",
            #                line_width=1,
            #                 line_dash='dash')

            fig.add_hline(y=avg_pv_daily, 
                            annotation_text= annotation_avg,
                            line_color='dimgrey',
                            annotation_position="bottom left",
                            line_width=1,
                             line_dash='dash')
#
            #fig.add_hline(y=max_pv_daily/1000, 
            #                annotation_text= annotation_max,
            #                line_color='dimgrey',
            #                annotation_position="bottom left",
            #                line_width=1,
            #                 line_dash='dash')
            #
            fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Time",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #dtick = 'D10',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title="Daily PV Yield in  kWh",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    #dtick='D3'
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          
        
            st.plotly_chart(fig, use_container_width=True)
            #fig.write_image("pv_yield_937_1.pdf")

    


    ######################################################################################################
    st.markdown("<h3 style='text-align: center'>Performance Ratio</h3>", unsafe_allow_html=True)
    
    col1, col2= st.columns([1,1])
    col1.markdown("<h3 style='text-align: center'>Daily</h3>", unsafe_allow_html=True)
    col2.markdown("<h3 style='text-align: center'>Monthly</h3>", unsafe_allow_html=True)
    with col1:
    
            #############
        fig = go.Figure([go.Bar(y=daily_data['PR'], x=daily_data.index, 
                                    name='Performance Ratio',
                                    marker_color='lightslategrey')],)

        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #dtick = 'd1',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Performance Ratio in %",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    tickformat='%',
                                    #dtick = 0.1,
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          
        
        st.plotly_chart(fig,use_container_width=True)
        #fig.write_image("PR_daily.pdf")
        
    with col2:
    
            #############
        
        fig = go.Figure([go.Bar(y=monthly_data['PR'], x=monthly_data.index, 
                                    name='Performance Ratio',
                                    marker_color='lightslategrey')],)
        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat="%b\n%Y", #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    dtick = 'M1',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Performance Ratio in %",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    tickformat='%',
                                    dtick = 0.1,
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          

        
        st.plotly_chart(fig,use_container_width=True)
        #fig.write_image("PR_month.pdf")
        
    
    ##################
    st.markdown("<h3 style='text-align: center'>Full Load Hours</h3>", unsafe_allow_html=True)
    
    col1, col2= st.columns([1,1])
    col1.markdown("<h3 style='text-align: center'>Daily</h3>", unsafe_allow_html=True)
    col2.markdown("<h3 style='text-align: center'>Monthly</h3>", unsafe_allow_html=True)
    
    
        
        
    with col1:
    
            #############
        fig = go.Figure([go.Bar(y=daily_data['Yf'], x=daily_data.index, 
                                    name='Vollaststunden',
                                    marker_color='lightslategrey')],)


        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #dtick = 'd1',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Full Load Hours in h",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          
        st.plotly_chart(fig,use_container_width=True)
        #fig.write_image("YF_daily.pdf")
        
    with col2:
        fig = go.Figure([go.Bar(y=monthly_data['Yf'], x=monthly_data.index, 
                                    name='Vollaststunden',
                                    marker_color='lightslategrey')],)

        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat="%b\n%Y", #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    dtick = 'M1',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Full Load Hours in h",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    #dtick = 1,
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          

    
        st.plotly_chart(fig,use_container_width=True)
        #fig.write_image("YF_month.pdf")
        
    ####### PR and Yf daily######
    
    #############PV Profile typical day
    st.markdown("<h3 style='text-align: center'>Hourly pv profile</h3>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=typ_day.index, 
                                y=typ_day['avg_pv_w'], name="PV Profile",
                                line_shape='linear',line_color='rgb(223,116,149)',line_width=4))
    
    fig.update_layout(  #title='Hourly grid availability profile USB',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Hour of the day",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[1,24],
                                    dtick = 1,
                                    ),
                                yaxis=dict(
                                    title=" Average PV Power",
                                    #showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    dtick = 50,
                                    ticks='outside',
                                    #tickformat='%',
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("hour_profile_pv.pdf")
    
    
    
    
with st.expander('Load Analysis'):
    
    st.markdown("<h3 style='text-align: center'>Load</h3>", unsafe_allow_html=True)
    
   
    col1, col2= st.columns([1,1])
    col1.markdown("<h3 style='text-align: center'>Load Power</h3>", unsafe_allow_html=True)
    col2.markdown("<h3 style='text-align: center'>Consumption</h3>", unsafe_allow_html=True)
    with col1:  

    
        #############
        fig = go.Figure()
       
        fig.add_trace(go.Scatter(x=df_load.index, 
                                    y=df_load['output_load'], name="load",fill='tozeroy',mode="lines", 
                                    line_color='lightslategrey',
                                    line_shape='linear',line_width=1))
        
        annotation_min= "<b>Min: "+str(min_load) +" W<b>"
        annotation_avg= "<b>Avg: "+str(avg_load) +" W<b>"
        annotation_max= "<b>Max: "+str(max_load) +" W<b>"
        fig.add_hline(y=min_load, 
                        annotation_text= annotation_min,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                        line_width=1,
                         line_dash='dash')

        fig.add_hline(y=avg_load, 
                        annotation_text= annotation_avg,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                        line_width=1,
                         line_dash='dash')

        fig.add_hline(y=max_load, 
                        annotation_text= annotation_max,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                        line_width=1,
                         line_dash='dash')

        
        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Time[d/m H:M]",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,110],
                                    
                                    ),
                                yaxis=dict(
                                    title=" Load in W",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                                    )          
        
        st.plotly_chart(fig, use_container_width=True)
        #fig.write_image("load_power.pdf")
    
    #################
    with col2:
        
        fig = go.Figure([go.Bar(y=daily_data['load_wh'], x=daily_data.index, 
                               name='Daily Electricity Consumption',
                                marker_color='coral')],)

        annotation_min= "<b>Min:"+str(min_load_daily) +" Wh<b>"
        annotation_avg= "<b>Avg: "+str(avg_load_daily*1000) +" Wh<b>"
        annotation_max= "<b>Max: "+str(max_load_daily) +" Wh<b>"
        annotation_sum= "<b>Total AAM Consumption: "+str(sum_load_daily) +" kWh<b>"
        fig.add_hline(y=min_load_daily, 
                        annotation_text= annotation_min,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                        
                        line_width=1,
                        line_dash='dash',
                        )

        fig.add_hline(y=avg_load_daily*1000, 
                        annotation_text= annotation_avg,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                      
                        line_width=1,
                         line_dash='dash')

        fig.add_hline(y=max_load_daily, 
                        annotation_text= annotation_max,
                        line_color='dimgrey',
                        annotation_position="bottom left",
                      
                     
                        line_width=1,
                         line_dash='dash')
        
        #fig.add_annotation(text=annotation_sum,
        #                    xref="paper", yref="paper",
        #                    x=0.95, y=0.05, showarrow=False,
        #                    align="center",
        #                    bordercolor="#c7c7c7",
        #                    borderwidth=2,
        #                    borderpad=4,
        #                    bgcolor="rgb(223,116,149)",
        #                    opacity=0.8,)
        #                    #ax=20,
        #                    #ay=-30,)
        
        
        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #dtick = '1d',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title="Comsumption per day in Wh",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[0,800],
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="bottom",
                                            y=0.05,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          
        
        st.plotly_chart(fig, use_container_width=True)
        #fig.write_image("consumption.pdf")

        
        #################
  
    st.markdown("<h3 style='text-align: center'>Cosumption separated by source</h3>", unsafe_allow_html=True)
    col1, col2= st.columns([3,1])
    
    
    with col1:
        fig = go.Figure()
        fig.add_bar(x=daily_data.index,y=daily_data['load_wh_bat'],name='bat',marker_color='MediumSeaGreen')
        fig.add_bar(x=daily_data.index,y=daily_data['load_wh_pv'],name='pv',marker_color='gold')
        fig.add_bar(x=daily_data.index,y=daily_data['load_wh_grid'],name='grid',marker_color='DarkSlateGrey')
        
        #fig.add_bar(x=daily_data.index,y=daily_data['load_wh'],name='all',marker_color='lightslategrey')
        fig.update_layout(barmode="relative")
                
        fig.update_layout(  #title='Hourly grid availability profile USB',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Day/Month",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[1,24],
                                    #dtick = 1,
                                    ),
                                yaxis=dict(
                                     title="Comsumption per day in  Wh",
                                    #showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    #dtick = 100,
                                    ticks='outside',
                                    #tickformat='%',
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=True,
                                legend=dict(title="",
                                            orientation="v",
                                            yanchor="top",
                                            y=0.99,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.99,
                                            ),
                                    )                             

        st.plotly_chart(fig, use_container_width=True)
        #fig.write_image("consumption_types.pdf")
    
    
    ###############################################
    with col2:
    
        labels = ['PV Direct','Bat','Grid']
        values = [load_kwh_pv, load_kwh_bat, load_kwh_grid]
        colors = ['gold','MediumSeaGreen','DarkSlateGrey']
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.8)])
        fig.update_traces(hoverinfo='label+percent', textinfo='percent', textfont_size=20,
                      marker=dict(colors=colors, line=dict(color='#000000', width=2)))
        fig.update_layout(annotations=[dict(text=str(load_kwh)+" kWh", x=0.5, y=0.5, font_size=20, showarrow=False)])
        st.plotly_chart(fig,use_container_width=True)
        

        
#############Load Profile typical day
    st.markdown("<h3 style='text-align: center'>Hourly Load Profile</h3>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=typ_day.index, 
                                y=typ_day['avg_load_w'], name="Load Profile",
                                line_shape='linear',line_color='coral'))
    
    fig.update_layout(  #title='Hourly grid availability profile USB',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="hour of the day",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    #tickformat='%d/%m %H:%M', #%H:%M',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[1,24],
                                    dtick = 1,
                                    ),
                                yaxis=dict(
                                    title=" Load in W",
                                    #showgrid=True,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #range=[140,250],
                                    dtick = 20,
                                    ticks='outside',
                                    #tickformat='%',
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=600, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=1.05,
                                            xanchor="center",
                                            traceorder='normal',
                                            x=0.5,
                                            ),
                                    )                             

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("hour_profile_load.pdf")
    
with st.expander('Battery Analysis'):
    st.markdown("<h3 style='text-align: center'>Battery Voltage</h3>", unsafe_allow_html=True)
    col1, col2= st.columns([3,1])
    col1.subheader('MPPT Battery Voltage')
    col2.subheader('Distribution')
    with col1:
    
        #############
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=system_data_time.index, 
                                    y=system_data_time['mppt_output_voltage'], name="Battery Voltage",
                                    line_shape='linear',line_color='gold'))
        
        fig.update_layout(#title='Grid Data',
                plot_bgcolor='white',
                xaxis=dict(
                    showline=True,
                    showgrid=True,
                    showticklabels=True,
                    linewidth=1.5,
                    ticks='outside',
                    title="Day/Month",
                    gridcolor='lightgrey',
                    linecolor='lightgrey',
                    mirror=True,
                    tickformat='%d/%m', #%H:%M',
                    tickfont=dict(
                        family='Fugue',
                        size=12,
                        color='rgb(82, 82, 82)'
                        ),
                ),
                    yaxis=dict(
                    title=" Battery Voltage in V",
                    showgrid=True,
                    zeroline=True,
                    showline=True,
                    linewidth=1.5,
                    ticks='outside',
                    linecolor='lightgrey',
                    mirror=True,
                    showticklabels=True,
                    gridcolor='lightgrey',
                    tickfont=dict(
                        family='Fugue',
                         size=12,
                        color='rgb(82, 82, 82)',),),)
        st.plotly_chart(fig, use_container_width=True)
    
    #################
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Box(y=system_data_time['mppt_output_voltage'],
                            marker_color = 'gold'))
        fig.update_layout(#title='Grid Data',
                plot_bgcolor='white',
                xaxis=dict(
                    showline=True,
                    showgrid=True,
                    showticklabels=True,
                    linewidth=1.5,
                    ticks='outside',
                    #title="Day/Month",
                    gridcolor='lightgrey',
                    linecolor='lightgrey',
                    mirror=True,
                    tickformat='%d/%m', #%H:%M',
                    tickfont=dict(
                        family='Fugue',
                        size=12,
                        color='rgb(82, 82, 82)'
                        ),
                ),
                    yaxis=dict(
                    #title=" Grid Voltage in V",
                    showgrid=True,
                    zeroline=True,
                    showline=True,
                    linewidth=1.5,
                    ticks='outside',
                    linecolor='lightgrey',
                    mirror=True,
                    showticklabels=True,
                    gridcolor='lightgrey',
                    tickfont=dict(
                        family='Fugue',
                         size=12,
                        color='rgb(82, 82, 82)',),),)
        st.plotly_chart(fig, use_container_width=True)
        
    ##################
    
    col1.subheader('Daily Min and Max MPPT Battery Voltage')
    col2.subheader('Distribution')
    with col1:
    
        #############
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_data.index, 
                                    y=daily_data['Bat_V_min'], name="Min",
                                    line_shape='linear',line_color='lightslategrey'))
  
        fig.add_trace(go.Scatter(x=daily_data.index, 
                                    y=daily_data['Bat_V_max'], name="Max",
                                    line_shape='linear',line_color='rgb(223,116,149)'))
        
        fig.update_layout(#title='Grid Data',
                                plot_bgcolor='white',
                                xaxis=dict(
                                    showline=True,
                                    showgrid=False,
                                    showticklabels=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    title="Time",
                                    gridcolor='lightgrey',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    tickformat='%d/%m',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    #dtick = 'D10',
                                    #range=[0,110],
                                    ),
                                yaxis=dict(
                                    title=" Battery Voltage in V",
                                    showgrid=False,
                                    zeroline=True,
                                    showline=True,
                                    linewidth=1.5,
                                    ticks='outside',
                                    linecolor='lightgrey',
                                    mirror=True,
                                    showticklabels=True,
                                    gridcolor='lightgrey',
                                    tickfont=dict(family="Fugue",size=12, color='Black'),
                                    range=[22,29],
                                    dtick=1
                                    ),
                                font=dict( family="Fugue", size=12, color='black'),
                                autosize=False,
                                width=300, height=300,
                                margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                showlegend=False,
                                legend=dict(title="",
                                            orientation="h",
                                            yanchor="bottom",
                                            y=0,
                                            xanchor="right",
                                            traceorder='normal',
                                            x=0.95,
                                            ),
                            )          
        
        st.plotly_chart(fig, use_container_width=True)
        #fig.write_image("bat_voltage_557.pdf")

    
    #################
    with col2:
        fig = go.Figure()
        fig.add_trace(go.Box(y=daily_data['Bat_V_max'],
                            marker_color = 'green'))
        fig.add_trace(go.Box(y=daily_data['Bat_V_min'],
                            marker_color = 'red'))
        fig.update_layout(#title='Grid Data',
                plot_bgcolor='white',
                xaxis=dict(
                    showline=True,
                    showgrid=True,
                    showticklabels=True,
                    linewidth=1.5,
                    ticks='outside',
                    #title="Day/Month",
                    gridcolor='lightgrey',
                    linecolor='lightgrey',
                    mirror=True,
                    tickformat='%d/%m', #%H:%M',
                    tickfont=dict(
                        family='Fugue',
                        size=12,
                        color='rgb(82, 82, 82)'
                        ),
                ),
                    yaxis=dict(
                    #title=" Grid Voltage in V",
                    showgrid=True,
                    zeroline=True,
                    showline=True,
                    linewidth=1.5,
                    ticks='outside',
                    linecolor='lightgrey',
                    mirror=True,
                    showticklabels=True,
                    gridcolor='lightgrey',
                    tickfont=dict(
                        family='Fugue',
                         size=12,
                        color='rgb(82, 82, 82)',),),)
        st.plotly_chart(fig, use_container_width=True)
        
    ##################
    
    #############battery voltage typical day
    st.markdown("<h3 style='text-align: center'>Hourly Profile of Battery Voltage</h3>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=typ_day.index, 
                                y=typ_day['avg_bat_v'], name="battery voltage Profile",
                                line_shape='linear',line_color='pink'))
    
    fig.update_layout(title='battery voltage profile',
            plot_bgcolor='white',
            xaxis=dict(
                showline=True,
                showgrid=True,
                showticklabels=True,
                linewidth=1.5,
                ticks='outside',
                title="hour",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                range=[1,24],
                dtick = 1,
                ticklen=1,
                #tickformat='',
                tickfont=dict(
                    family='Fugue',
                    size=12,
                    color='rgb(82, 82, 82)'
                    ),
            ),
                yaxis=dict(
                title=" Load in W",
                showgrid=True,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                #range=[0,1],
                #ticklen=0.1,
                #dtick = 0.1,
                ticks='outside',
                #tickformat='%',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(
                    family='Fugue',
                     size=12,
                    color='rgb(82, 82, 82)',),),)
    st.plotly_chart(fig, use_container_width=True)
    

with st.expander('CO2 savings Analysis '):
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Bar(x=daily_data.index,y=daily_data['co2_load'],
                         name='saved CO2',marker_color='rgb(223,116,149)'),secondary_y=False,)
    
    fig.add_trace(go.Bar(x=daily_data.index,y=daily_data['cost_savings_load'],
                         name='fuel cost saved',marker_color='pink'),secondary_y=True)
  
    fig.update_layout(title='saved CO2 per day & fuel expenses savings per day',
            plot_bgcolor='white',
            barmode='group',
            showlegend=False,
            xaxis=dict(
                showline=True,
                showgrid=False,
                showticklabels=True,
                linewidth=1.5,
                ticks='outside',
                title="Day/Month",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                tickformat='%d/%m', #%H:%M',
                tickfont=dict(
                    family='Fugue',
                    size=12,
                    color='rgb(82, 82, 82)'
                    ),
            ),
                yaxis=dict(
                title="saved CO2 in kg Co2",
                showgrid=True,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                ticks='outside',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(
                    family='Fugue',
                     size=12,
                    color='rgb(82, 82, 82)',),),)
    
    fig.update_yaxes(title_text="fuel expenses savings per day", 
                         secondary_y=True,
                         ticks='outside',
                         tickfont=dict(
                                family='Fugue',
                                size=12,
                                color='rgb(82, 82, 82)',),
                         #range=[0,600]
                         )
    st.plotly_chart(fig,use_container_width=True)
    
    #########################################
        
    col1, col2= st.columns([1,1])
    with col1:
        st.info('Total CO2 savings are '+str( co2_load)+'kg CO2' )
    
    with col2:
        st.info('Total fuel expenses savings are: $'+str(  cost_savings_load ))
        
    ##########################################

    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(go.Bar(x=daily_data.index,y=daily_data['co2_pv'],
                         name='PV',marker_color='rgb(133,187,101)'),secondary_y=False,)

    
    fig.add_trace(go.Bar(x=daily_data.index,y=daily_data['cost_savings_pv'],
                         name='PV',marker_color='rgb(133,187,101)'),secondary_y=True,)
    
    fig.update_layout(title='saved CO2 per day & fuel expenses savings per day (PV Yield)',
            plot_bgcolor='white',
            barmode='group',
            showlegend=False,
            xaxis=dict(
                showline=True,
                showgrid=False,
                showticklabels=True,
                linewidth=1.5,
                ticks='outside',
                title="Day/Month",
                gridcolor='lightgrey',
                linecolor='lightgrey',
                mirror=True,
                tickformat='%d/%m', #%H:%M',
                tickfont=dict(
                    family='Fugue',
                    size=12,
                    color='rgb(82, 82, 82)'
                    ),
            ),
                yaxis=dict(
                title="saved CO2 in kg Co2",
                showgrid=True,
                zeroline=True,
                showline=True,
                linewidth=1.5,
                ticks='outside',
                linecolor='lightgrey',
                mirror=True,
                showticklabels=True,
                gridcolor='lightgrey',
                tickfont=dict(
                    family='Fugue',
                     size=12,
                    color='rgb(82, 82, 82)',),),)
    
    fig.update_yaxes(title_text="fuel expenses savings per day", 
                         secondary_y=True,
                         ticks='outside',
                         tickfont=dict(
                                family='Fugue',
                                size=12,
                                color='rgb(82, 82, 82)',),
                         #range=[0,600]
                         )
    st.plotly_chart(fig,use_container_width=True)
    
    #########################################
        
    col1, col2= st.columns([1,1])
    with col1:
        st.info('Total CO2 savings are '+str(  co2_pv )+'kg CO2' )
    
    with col2:
        st.info('Total fuel expenses savings are: $'+str(cost_savings_pv))
    ##########################################
    
    
    
with st.expander('Overview All systems'):

    #st.dataframe(df_output)
    #############################################################################################################################################

    fig = go.Figure()


    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['grid_avl_all_usb'], name='usable grid availability',marker_color='lightslategrey'))
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=(df_output['aam_avl_all']-df_output['grid_avl_all_usb']), name='aam availability', marker_color='rgb(223,116,149)'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    fig.update_layout(xaxis={'categoryorder':'total descending'},
                     barmode='relative')


    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Availability',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("availability_all.pdf") #####this one

    #############################################################################################################################################
    df_output.sort_values(by=['co2_pv'],ascending=False,inplace=True)
    #df_output
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['co2_pv'], name='CO2 and cost savings(PV method)', marker_color='rgb(223,116,149)'),secondary_y=False)
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['co2_load'], name='CO2 and cost savings(Load method)',marker_color='lightslategrey'),secondary_y=False)

    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['cost_savings_pv'], marker_color='rgb(223,116,149)',showlegend=False),secondary_y=True)
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['cost_savings_load'],marker_color='lightslategrey',showlegend=False),secondary_y=True)

    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    #fig.update_layout(xaxis={'categoryorder':'total descending'})


    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='CO2 savings in kg',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.9,
                                                ),
                                        )         
    fig.update_yaxes(title_text=" Cost savings in USD", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             #range=[0.38,0.50],
                             #dtick = 0.1,
                             #tickformat='%',
                             )
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("co2_cost_savings_all.pdf") #####this one
    
    
#################################################################################
    df_output.sort_values(by=['pv_kwh'],ascending=False,inplace=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])


    fig.add_trace(go.Scatter(x=df_output['aam_name'], y=df_output['grid_avl_day'], name='grid_avl_day', marker_color='darkslategrey',line_width=3),secondary_y=True)
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['pv_kwh'], name='pv_kwh',marker_color='rgb(223,116,149)'),secondary_y=False)
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    #fig.update_layout(xaxis={'categoryorder':'total descending'})


    fig.update_layout(              #title='Hourly grid availability profile USB',

                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='PV Yield in kWh',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        dtick = 30,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),)

    fig.update_yaxes(title_text=" Probability of grid availability in %", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             #range=[0.38,0.50],
                             dtick = 0.1,
                             tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("pv_gridday_all.pdf")

    #################################################################################
    df_output.sort_values(by=['avg_pv_daily'],ascending=False,inplace=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])


    fig.add_trace(go.Scatter(x=df_output['aam_name'], y=df_output['grid_avl_day'], name='grid availability(day)', marker_color='darkslategrey',line_width=3),secondary_y=True)
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['avg_pv_daily'], name='Average PV yield daily',marker_color='rgb(223,116,149)'),secondary_y=False)
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    #fig.update_layout(xaxis={'categoryorder':'total descending'})


    fig.update_layout(              #title='Hourly grid availability profile USB',

                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='PV Yield in kWh',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        dtick = 0.5,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),)

    fig.update_yaxes(title_text=" Probability of grid availability in %", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             #range=[0.38,0.50],
                             dtick = 0.1,
                             tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("pv_gridday_all.pdf")
#################################################################################

    df_output.sort_values(by=['avg_load_daily'],ascending=False,inplace=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])


    fig.add_trace(go.Scatter(x=df_output['aam_name'], y=df_output['avg_load'], name='avg load', marker_color='darkslategrey',line_width=3),secondary_y=True)
    fig.add_trace(go.Bar(x=df_output['aam_name'], y=df_output['avg_load_daily'], name='avg daily consumption',marker_color='rgb(223,116,149)'),secondary_y=False)
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    #fig.update_layout(xaxis={'categoryorder':'total descending'})


    fig.update_layout(              #title='Hourly grid availability profile USB',

                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Average daily consumption in kWh',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 30,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),)

    fig.update_yaxes(title_text=" Average Load in W", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             #range=[0.38,0.50],
                             #dtick = 0.1,
                             #tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("load_consump_all.pdf")

#################################################################################


    ##############################################################################################################

    df_output['aam_name']=df_output['aam_name'].apply(int)
    df_output.sort_values(by=['aam_name'],ascending=False,inplace=True)
    aam_main.sort_values(by=['aam_name'],ascending=False,inplace=True)
    #df_output['aam_name']=df_output['aam_name'].apply(str)
    aam_main.reset_index(drop=True, inplace=True)
    df_output.reset_index(drop=True, inplace=True)
    #aam_main
    #df_output

    bat_vergleich= aam_main
    bat_vergleich['avg_load_daily']=df_output['avg_load_daily']
    bat_vergleich['grid_avl_all_usb']=df_output['grid_avl_all_usb']
    bat_vergleich['grid_avl_day_usb']=df_output['grid_avl_day_usb']
    bat_vergleich['grid_avl_oh_usb']=df_output['grid_avl_oh_usb']
    bat_vergleich['pv_kwh']=df_output['pv_kwh']
    bat_vergleich['PR_avg']=(df_output['PR_aug']+df_output['PR_aug'])/2
    bat_vergleich['aam_avl_all']=df_output['aam_avl_all']
    bat_vergleich['aam_avl_day']=df_output['aam_avl_day']
    bat_vergleich['aam_avl_oh']=df_output['aam_avl_oh']
    bat_vergleich['avg_load']=df_output['avg_load']

    #bat_vergleich

    bat_vergleich.sort_values(by=['avg_load_daily'],ascending=False,inplace=True)
    fig = make_subplots(specs=[[{"secondary_y": True}]])



    #x1=[df_output['aam_name'],aam_main['bat_size']]
    #fig.add_trace(go.Scatter(x=x1, y=df_output['avg_load'], name='avg load', marker_color='darkslategrey',line_width=3),secondary_y=True)
    x=[bat_vergleich['aam_name'],bat_vergleich['bat_size']]
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['pv_kwh'], name='pv_kwh',line_color='green'),secondary_y=True)
    fig.add_trace(go.Scatter(x=x, y=bat_vergleich['avg_load_daily'], name='avg_load_daily',line_color='lightslategray'),secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=bat_vergleich['grid_avl_all_usb']*100, name='grid_avl_all_usb',line_color='red'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['PR_avg']*100, name='PR_avg',line_color='coral'),secondary_y=True)
    fig.add_trace(go.Scatter(x=x, y=bat_vergleich['aam_avl_all']*100, name='aam_avl_all',line_color='pink'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['aam_avl_day']*100, name='aam_avl_day',line_color='pink'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['avg_load'], name='avg_load',line_color='GoldenRod'),secondary_y=True)

    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['grid_avl_day_usb']*100, name='grid_avl_day_usb',line_color='blue'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['PR_avg']*100, name='PR_avg',line_color='coral'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['aam_avl_day']*100, name='aam_avl_day',line_color='lightblue'),secondary_y=True)


    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['grid_avl_oh_usb']*100, name='grid_avl_oh_usb',line_color='grey'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['PR_avg']*100, name='PR_avg',line_color='coral'),secondary_y=True)
    #fig.add_trace(go.Scatter(x=x, y=bat_vergleich['aam_avl_oh']*100, name='aam_avl_oh',line_color='lightgrey'),secondary_y=True)

    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['avg_pv_daily'], name='avg_pv_daily'))
    #fig.add_trace(go.Bar(x=mes['aam_name'], y=mes['load_kwh']/100, name='avg_pv_daily'))


    #fig.update_layout(xaxis={'categoryorder':'total descending'})


    fig.update_layout(              #title='Hourly grid availability profile USB',

                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="System ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Average daily consumption in kWh',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 30,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="left",
                                                traceorder='normal',
                                                x=1.1,
                                                ),)

    fig.update_yaxes(title_text=" grid_avl_all_usb/ pv_kwh ", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             #range=[0.38,0.50],
                             #dtick = 0.1,
                             #tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("load_consump_all.pdf")
    #############################################################################################################################
    fig = go.Figure()

    fig.add_trace(go.Bar(x=maraba_grid['aam_name'], y=maraba_grid['avg_grid_daily_all'], name='avg_grid_daily_all',marker_color='lightslategrey'))

    fig.update_layout(xaxis={'categoryorder':'total descending'})

    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="system ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Daily grid time in h',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        dtick = 2,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=200, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    #showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("Daily_grid_time_maraba.pdf")

    #################################################################################


    fig = go.Figure()

    fig.add_trace(go.Bar(x=maraba_grid['aam_name'], y=maraba_grid['avg_bl_duration'], name='avg_bl_duration',marker_color='lightslategrey'))

    fig.update_layout(xaxis={'categoryorder':'total descending'})

    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="system ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='avg_bl_duration',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        dtick = 2,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=200, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    #showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("Daily_grid_time_maraba.pdf")

    #################################################################################


    fig = go.Figure()

    fig.add_trace(go.Bar(x=ongrid['aam_name'], y=ongrid['avg_bl_duration'], name='Average blackout duration',marker_color='rgb(223,116,149)'))
    fig.add_trace(go.Bar(x=ongrid['aam_name'], y=ongrid['avg_bl_nu_d'], name='Daily average number of blackouts',marker_color='lightslategrey'))

    fig.update_layout(xaxis={'categoryorder':'total descending'})

    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="system ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Average blackout duration in h / <br> daily average number of blackouts ',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        dtick = 2,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    #showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("bl_grid.pdf") this one

    #################################################################################


    fig = go.Figure()

    fig.add_trace(go.Bar(x=maraba_grid['aam_name'], y=maraba_grid['avg_bl_duration'], name='Average blackout duration',marker_color='rgb(223,116,149)'))
    fig.add_trace(go.Bar(x=maraba_grid['aam_name'], y=maraba_grid['avg_bl_nu_d'], name='Daily average number of blackouts',marker_color='lightslategrey'))
    #fig.add_trace(go.Bar(x=maraba_grid['aam_name'], y=maraba_grid['aam_avl_all']*5, name='Daily average number of blackouts',marker_color='red'))

    fig.update_layout(xaxis={'categoryorder':'total descending'})

    fig.update_layout(              #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="system ID",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[1,24],
                                        #dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title='Average blackout duration in h / <br> Daily average number of blackouts ',
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,10],
                                        dtick = 2,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=300, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    #showlegend=True,
                                    legend=dict(title="",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("bl_grid_maraba.pdf")


with st.expander('Daily Profiles'):
    
    
    grid_avl_hourly = pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/grid_avl_hourly.csv",index_col=['UTC'])## Import Data from the merge
    grid_avl_usb_hourly = pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/grid_avl_usb_hourly.csv",index_col=['UTC'])## Import Data from the merge
    load_hourly = pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/load_hourly.csv",index_col=['UTC'])## Import Data from the merge
    pv_hourly = pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/pv_hourly.csv",index_col=['UTC'])## Import Data from the merge
    bat_hourly = pd.read_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/bat_hourly.csv",index_col=['UTC'])## Import Data from the merge


    households_grid_avl_hourly= grid_avl_hourly[households['aam_name']]
    households_grid_avl_hourly['mean'] = households_grid_avl_hourly.mean(axis=1)
    #households_grid_avl_hourly

    household_ongrid_grid_avl_hourly=grid_avl_hourly[grid_avl_hourly[households['aam_name']].columns[grid_avl_hourly[households['aam_name']].columns.isin(ongrid['aam_name'])]]
    household_ongrid_grid_avl_hourly['mean'] = household_ongrid_grid_avl_hourly.mean(axis=1)
    #household_ongrid_grid_avl_hourly

    #########################################################################################

    all_grid_avl_hourly=grid_avl_hourly[ongrid['aam_name']]
    all_grid_avl_hourly['mean'] = all_grid_avl_hourly.mean(axis=1)
    #all_grid_avl_hourly

    all_ongrid_load_hourly=load_hourly[ongrid['aam_name']]
    all_ongrid_load_hourly['mean'] = all_ongrid_load_hourly.mean(axis=1)
    #all_ongrid_load_hourly



    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=load_hourly.index, y=all_ongrid_load_hourly['mean'],name= 'Average Load',line_color='rgb(223,116,149)'),secondary_y=False)
    fig.add_trace(go.Scatter(x=grid_avl_usb_hourly.index, y=all_grid_avl_hourly['mean'],name= 'Average Grid Availability',line_color='lightslategrey'),secondary_y=True)

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Average Load in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[40,210],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                                )
    fig.update_yaxes(title_text=" Probability of grid availability in %", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             range=[0.38,0.50],
                             dtick = 0.05,
                             tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("load_availability_all_grid.pdf") #############This one

    #################################################################################################

    household_load_hourly=load_hourly[households['aam_name']]
    household_load_hourly['mean'] = household_load_hourly.mean(axis=1)
    #household_load_hourly


    mes_load_hourly=load_hourly[mes['aam_name']]
    mes_load_hourly['mean'] = mes_load_hourly.mean(axis=1)
    #mes_load_hourly


    #mes_load_hourly.to_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/mes_load_hourly.csv")
    #household_load_hourly.to_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/household_load_hourly.csv")

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=mes_load_hourly.index, y=mes_load_hourly['mean'],name= 'Average Load MEs',line_color='rgb(223,116,149)'))
    fig.add_trace(go.Scatter(x=household_load_hourly.index, y=household_load_hourly['mean'] ,name= 'Average Load Households',line_color='lightslategrey'))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="Hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Average Load in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,200],
                                        dtick = 50,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=0.05,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.95,
                                                ),
                                                )

    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("households_mes_load_all.pdf")
    #####################################################################################

    maraba_grid_avl_hourly=grid_avl_hourly[grid_avl_hourly[maraba['aam_name']].columns[grid_avl_hourly[maraba['aam_name']].columns.isin(ongrid['aam_name'])]]
    #maraba_grid_avl_hourly['mean'] = maraba_grid_avl_hourly.mean(axis=1)
    #maraba_grid_avl_hourly

    fig = go.Figure()

    for i in maraba_grid_avl_hourly.columns:
        fig.add_trace(go.Scatter(x=maraba_grid_avl_hourly.index, y=maraba_grid_avl_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 2,
                                        ),
                                    yaxis=dict(
                                        title=" Probability of grid availability in %",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,0.7],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=400, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="System ID",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="left",
                                                traceorder='normal',
                                                x=1.05,

                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("grid_hourly_profile_maraba.pdf")

    #####################################################################################

    grid_pv_hourly=pv_hourly[ongrid['aam_name']]
    grid_pv_hourly['mean'] = grid_pv_hourly.mean(axis=1)
    #grid_pv_hourly

    offgrid_pv_hourly=pv_hourly[offgrid['aam_name']]
    offgrid_pv_hourly['mean'] = offgrid_pv_hourly.mean(axis=1)
    #offgrid_pv_hourly

    fig = go.Figure()

    #fig.add_trace(go.Scatter(x=grid_pv_hourly.index, y=grid_pv_hourly['mean'],name='ongrid'))
    #fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=offgrid_pv_hourly['mean'],name='offgrid'))
    #fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['943'],name='943'))
    fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['654'],name='aam_654',line_color='rgb(223,116,149)'))
    fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['283'],name='aam_283',line_color='lightslategrey'))



    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 2,
                                        ),
                                    yaxis=dict(
                                        title=" Average PV Power in W ",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,0.7],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(#title="System ID",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,

                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("pv_hourly_283_654.pdf")######this one
    #####################################################################################

    grid_bat_hourly=bat_hourly[ongrid['aam_name']]
    grid_bat_hourly['mean'] = grid_bat_hourly.mean(axis=1)
    #grid_bat_hourly

    offgrid_bat_hourly=bat_hourly[offgrid['aam_name']]
    offgrid_bat_hourly['mean'] = offgrid_bat_hourly.mean(axis=1)
    #offgrid_bat_hourly

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=grid_bat_hourly.index, y=grid_bat_hourly['mean'],name='ongrid',line_color='rgb(223,116,149)'))
    fig.add_trace(go.Scatter(x=offgrid_bat_hourly.index, y=offgrid_bat_hourly['mean'],name='offgrid',line_color='lightslategrey'))
    #fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['943'],name='943'))
    #fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['654'],name='aam_654',line_color='rgb(223,116,149)'))
    #fig.add_trace(go.Scatter(x=offgrid_pv_hourly.index, y=pv_hourly['283'],name='aam_283',line_color='lightslategrey'))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 2,
                                        ),
                                    yaxis=dict(
                                        title=" Battery voltage in V",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,0.7],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(#title="System ID",
                                                orientation="v",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="right",
                                                traceorder='normal',
                                                x=0.99,

                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("bat_hourly_grid_offgrid.pdf")######this one

    #####################################################################################
    fig = go.Figure()

    for i in mes_load_hourly.columns:
        fig.add_trace(go.Scatter(x=mes_load_hourly.index, y=mes_load_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Probability grid availability in %",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
                #fig.write_image("hour_profile_usb.pdf")
    fig = go.Figure()

    for i in grid_avl_hourly.columns:
        fig.add_trace(go.Scatter(x=grid_avl_hourly.index, y=grid_avl_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Probability grid availability in %",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,1],
                                        dtick = 0.1,
                                        ticks='outside',
                                        tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
                #fig.write_image("hour_profile_usb.pdf")

    fig = go.Figure()

    for i in grid_avl_usb_hourly.columns:
        fig.add_trace(go.Scatter(x=grid_avl_usb_hourly.index, y=grid_avl_usb_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Probability grid availability in %",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,1],
                                        dtick = 0.1,
                                        ticks='outside',
                                        tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)

    fig = go.Figure()

    for i in load_hourly.columns:
        fig.add_trace(go.Scatter(x=load_hourly.index, y=load_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Average Load in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)

    fig = go.Figure()

    ##############################################################################################

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=load_hourly.index, y=load_hourly['524'],line_color='goldenRod',line_width=2,name='Day-Only'))

    fig.add_trace(go.Scatter(x=load_hourly.index, y=load_hourly['1076'],line_color='darkslategrey',line_width=2,name='All-Day'))

    fig.add_trace(go.Scatter(x=load_hourly.index, y=load_hourly['1167'],line_color='rgb(223,116,149)',line_width=2,name='Opening-Hours'))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title="Load in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[0,600],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="top",
                                                y=0.99,
                                                xanchor="left",
                                                traceorder='normal',
                                                x=0.01,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)
    #fig.write_image("load_profiles_aam.pdf")
    #########################################################################################################################
    fig = go.Figure()

    for i in load_hourly.columns:
        fig.add_trace(go.Scatter(x=pv_hourly.index, y=pv_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title="PV Input in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)

    fig = go.Figure()

    for i in load_hourly.columns:
        fig.add_trace(go.Scatter(x=bat_hourly.index, y=bat_hourly[i],name=i))

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title="Bat voltage in V",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                        )                             
    st.plotly_chart(fig, use_container_width=True)

    #####################################################################################
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=load_hourly.index, y=load_hourly['mean'],name= 'Average Load',line_color='rgb(223,116,149)'),secondary_y=False)
    fig.add_trace(go.Scatter(x=grid_avl_usb_hourly.index, y=grid_avl_usb_hourly['mean'],name= 'Average Grid Availability',line_color='lightslategrey'),secondary_y=True)

    fig.update_layout(  #title='Hourly grid availability profile USB',
                                    plot_bgcolor='white',
                                    xaxis=dict(
                                        showline=True,
                                        showgrid=False,
                                        showticklabels=True,
                                        linewidth=1.5,
                                        ticks='outside',
                                        title="hour of the day",
                                        gridcolor='lightgrey',
                                        linecolor='lightgrey',
                                        mirror=True,
                                        #tickformat='%d/%m %H:%M', #%H:%M',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        range=[1,24],
                                        dtick = 1,
                                        ),
                                    yaxis=dict(
                                        title=" Average Load in W",
                                        #showgrid=True,
                                        zeroline=True,
                                        showline=True,
                                        linewidth=1.5,
                                        linecolor='lightgrey',
                                        mirror=True,
                                        showticklabels=True,
                                        gridcolor='lightgrey',
                                        tickfont=dict(family="Fugue",size=12, color='Black'),
                                        #range=[0,1],
                                        #dtick = 0.1,
                                        ticks='outside',
                                        #tickformat='%',
                                        ),
                                    font=dict( family="Fugue", size=12, color='black'),
                                    autosize=False,
                                    width=600, height=300,
                                    margin=dict(l=15, r=15, b=15, t=15,  pad=2),
                                    showlegend=True,
                                    legend=dict(title="",
                                                orientation="h",
                                                yanchor="bottom",
                                                y=1.05,
                                                xanchor="center",
                                                traceorder='normal',
                                                x=0.5,
                                                ),
                                                )
    fig.update_yaxes(title_text=" Probability grid availability in %", 
                             secondary_y=True,
                             ticks='outside',
                             tickfont=dict(
                                    family='Fugue',
                                    size=12,
                                    color='rgb(82, 82, 82)',),
                             range=[0.14,0.3],
                             dtick = 0.1,
                             tickformat='%',
                             )

    st.plotly_chart(fig, use_container_width=True)
with st.expander('Raw Data'):
    st.subheader('AAM Main')
    st.dataframe(aam_main)
    st.subheader('DF Output')
    st.dataframe(df_output)
    st.subheader('data for grid')
    st.dataframe(df_grid)
    st.dataframe(df_grid_evt)
    st.dataframe(df_grid_evt_on)
    st.dataframe(df_grid_evt_off)
    
    
    st.subheader('hour data')
    st.dataframe(hour_data)
    
    st.subheader('typical day')
    st.dataframe(typ_day)
    
    st.subheader('typical day_all')
    st.dataframe(typ_day_all)
    
    st.subheader('typical week')
    st.dataframe(typ_week)

    st.subheader('daily data')
    st.dataframe(daily_data)
    st.write(grid_on_all, grid_off_all,avg_grid_daily_all,min_pv_daily)
    st.subheader('daily data day')
    st.dataframe(daily_data_day)
    st.subheader('daily data opening hours')
    st.dataframe(daily_data_oh)
    st.subheader('monthly data')
    st.dataframe( monthly_data)
    st.subheader('data for load')
    st.dataframe(df_load)
    
    st.dataframe(sum_up_data)
    #st.dataframe(daily_data_day)
    st.subheader('solar radiation data')

    st.dataframe(solar_radiation)
    st.dataframe(solar_radiation_m)
    st.dataframe(solar_radiation_d)
    
    #st.dataframe(five_min_data)
    #st.dataframe(typ_day_min)
    
#st.line_chart(df_inverter.battery_voltage,)


