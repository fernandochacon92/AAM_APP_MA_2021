#sql data holen und darstellen
#solcast forecast
#app hochladen

#cd A2EI_PY/AAM_APP & streamlit run MA_FC_AAM_APP_make_data.py

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
aam_name= str(st.sidebar.selectbox('AAM ID', ['0','206','283','316','376','511','524','527','528','557','563','576','602','645','654','661','663','691','698','937','943','945','1076','1167']))#Set System Name
bat_size= st.sidebar.selectbox('Select Battery Size:', ['50Ah','100Ah'], index=0)

col1, col2,col3,col4= st.columns([1,1,1,1])
with col1:
    gen_consump= float(st.text_input('Generator Fuel Consumption in liter per kWh', 2))#liter/kwh
with col2:
    co2_fuel=float(st.text_input('Fuel CO^2 Emission kgCO2/liter', 2.64))#kgco2/liter
with col3:
    co2_grid=float(st.text_input('Grid CO^2 Emission kgCO2/kWh', 0.43963136))#kgco2/kWh
with col4:
    usd_fuel=float(st.text_input('Fuel Price USD/liter', 0.4))#USD/liter
        
households=['524','563','645','654','698','937','945','1076']
me=['206','283','316','376','511','527','528','576','602','663','691','943','1167']
ongrid=['283','376','524','527','563','576','602','698','943','945','1076','1167']
active=['661','528']
offgrid=['316','557','654','663','691']
gen=['206','645','511']
maraba=['206','283','316','376','527','576','602','937','943','1076']


path2merges= "use_data/use_"+aam_name+".csv"#Set Path for merges 
path2locations= "locations.csv" 



#Set time from where Merge should start
time_start=st.sidebar.date_input('start',value=(datetime(2021, 8, 1)))
time_end=st.sidebar.date_input('end',value=(datetime(2021, 9, 30)))

#import data set
system_data_all = pd.read_csv(path2merges ,parse_dates=['UTC'],index_col=['UTC'])## Import Data from the merge
system_data_all.sort_index(inplace=True)


system_data_time = system_data_all[time_start : time_end]

#import aam system information 
aam_main=pd.read_csv("aam_main.csv",index_col='aam_name')
aam_main
## Solar radiation data to calculate the performance ration of PV system

solar_radiation = pd.read_csv("pv_data_2005_2016.csv",
                                 sep=',',
                                parse_dates=['Month'],
                                index_col=['Month'])#set Timestamp column as index

solar_radiation['month'] = pd.DatetimeIndex(solar_radiation.index).month
#solar_radiation_m.to_datetime('Month', format='%m')
pv_location=st.sidebar.selectbox('Select solar radiation location:', ['Abuja','Lagos','Cross_River'], index=0)
solar_radiation_m=pd.DataFrame(columns=[])
solar_radiation_m[pv_location]=solar_radiation[pv_location].resample('M').sum()
dates = pd.date_range('2021-01-01', '2021-12-31', freq='D')

solar_radiation_d=pd.DataFrame(columns=[])                               
solar_radiation_d[pv_location]= solar_radiation[pv_location].reindex(dates, method='ffill')
solar_radiation_d[pv_location]= solar_radiation_d[pv_location]/solar_radiation_d.index.daysinmonth

## Separate data into Inverter, MPPT and MCU Data

df_inverter=pd.DataFrame(system_data_all, columns=['input_fault_voltage','output_voltage','output_current','output_frequency','battery_voltage','temperature','status','output_load','input_voltage','aam_on_time','aam_off_time'])
df_mppt=pd.DataFrame(system_data_all, columns=['charging_input_voltage','charging_input_current','charging_output_voltage','charging_ouput_current','discharging_output_voltage','discharging_output_current','temperature_inside','Temperature_power_components','Temperature_battery','SOC','Battery Status','PV_W_on'])
df_mcu=pd.DataFrame(system_data_all, columns=['peak_voltage'])

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
system_data_time['PV_E_Wh'].replace(np.nan,0 ,inplace=True)

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

#five_min_data= pd.DataFrame(columns=['grid_avl_h','load_w_h','pv_w_h'])
#five_min_data['grid_avl_min']=df_grid['grid_avl'].resample('5min').mean()
#five_min_data['load_w_min']=df_load['output_load'].resample('5min').mean()
#five_min_data['pv_w_min']=system_data_time['PV_W'].resample('5min').mean()
#five_min_data['bat_v_min']=df_mppt['charging_output_voltage'].resample('5min').mean()

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


PR_aug=round(monthly_data['PR'].iloc[0],2)
PR_sep=round(monthly_data['PR'].iloc[1],2)

Yf_aug=round(monthly_data['Yf'].iloc[0],2)
Yf_sep=round(monthly_data['Yf'].iloc[1],2)




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



################################################################################
#Write down some data :)


df_output = pd.read_csv("data_output.csv",index_col='aam_name')

df_output

if int(aam_name) in df_output.index:
    df_output.drop(index=int(aam_name), inplace=True)

df_output

df_output_log=[[int(aam_name),grid_avl_all,grid_avl_all_usb,grid_avl_day,grid_avl_day_usb,grid_avl_oh,grid_avl_oh_usb,aam_avl_all,aam_avl_day,aam_avl_oh,avg_grid_daily_all,avg_grid_daily_day,avg_grid_daily_oh,avg_bl_duration,avg_bl_nu_d,avg_bl_nu_m,pv_kwh,avg_pv_daily,PR_aug,PR_sep,Yf_aug,Yf_sep,avg_load,avg_load_daily,load_kwh,load_kwh_pv,load_kwh_grid,load_kwh_bat,co2_load,cost_savings_load,co2_pv,cost_savings_pv]]

df_output_log=pd.DataFrame(df_output_log,columns=['aam_name','grid_avl_all','grid_avl_all_usb','grid_avl_day','grid_avl_day_usb','grid_avl_oh','grid_avl_oh_usb','aam_avl_all','aam_avl_day','aam_avl_oh','avg_grid_daily_all','avg_grid_daily_day','avg_grid_daily_oh','avg_bl_duration','avg_bl_nu_d','avg_bl_nu_m','pv_kwh','avg_pv_daily','PR_aug','PR_sep','Yf_aug','Yf_sep','avg_load','avg_load_daily','load_kwh','load_kwh_pv','load_kwh_grid','load_kwh_bat','co2_load','cost_savings_load','co2_pv','cost_savings_pv'])
df_output_log
#df_output['avg_pv_daily']=df_output['avg_pv_daily']



#df_output.reset_index()

##df_output['aam_name']=df_output['aam_name'].apply(str)

df_output_log.set_index(['aam_name'],inplace=True)
df_output=df_output.append(df_output_log)
df_output_log
df_output

#df_output.to_csv("C:/Users/ThinkPad X1 Carbon/A2EI_PY/AAM_APP/ma_fc_data/data_output.csv")

df_output_1=pd.DataFrame(df_output,columns=['aam_name','grid_avl_all','grid_avl_all_usb','grid_avl_day','grid_avl_day_usb','grid_avl_oh','grid_avl_oh_usb','aam_avl_all','aam_avl_day','aam_avl_oh','PR_aug','PR_sep'])
#df_output_1

df_output_2=pd.DataFrame(df_output,columns=['aam_name','avg_grid_daily_all','avg_grid_daily_day','avg_grid_daily_oh','avg_bl_duration','avg_bl_nu_d','avg_bl_nu_m','pv_kwh','avg_pv_daily','Yf_aug','Yf_sep','avg_load','load_kwh','load_kwh_pv','load_kwh_grid','load_kwh_bat'])
#df_output_2
