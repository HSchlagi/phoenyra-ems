 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 1 / 19 
BMS Communication Protocol with EMS via Modbus 
1. Introduction 
This document describes in details of the communication protocol between the BMS and the EMS via Modbus for ESS Container 
(INF5015K050PG1&INF4179K050PG1). 
Xiamen Hithium Energy Storage Technology Co., Ltd. (“Hithium’’) offers this document as the standard limited document. The 
content of this document is supposed to be checked and updated when necessary. Please contact Hithium or your distributors 
for the latest version. 
This document is intended to be used for information purpose and by specific addressees, which may contain information that 
is confidential, you may not reproduce or distribute in any form or by any means. 
2. Command Parsing 
2.1. Telemetry Command 
2.1.1. Read Holding Register 03H 
Function Code: 03H 
Request: Monitor the background 
Table 2-1 Read hold register command to send data 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Start register address 
addr 
2×1 
UINT 
 
Number of registers 
cnt 
2×1 
UINT 
<=120 
Response:  
Table 2-2 Read hold register command reply data 
2.1.2. Read Input Register 04H 
Function Code: 04H 
Request: Monitor the background 
Table 2-3 Read input register command to send data 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Start register address 
addr 
2×1 
UINT 
 
Number of registers 
cnt 
2×1 
UINT 
<=120 
 
 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Number of subsequent 
bytes 
len 
1 
BYTE 
len = 2×cnt 
Data 
data 
2×cnt 
UINT 
 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 2 / 19 
Response:  
Table 2-4 Read input register command reply data 
2.2. Remote Signaling Command 
2.2.1. Read Discrete Input Register 
Function Code: 02H 
Request: Monitor the background 
Table 2-5 Read discrete input register command to send data 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Start register address 
addr 
2×1 
UINT 
 
Number of registers 
cnt 
2×1 
UINT 
<=2000 
Response:  
Table 2-6 Read input register command reply data 
Note: The data type in the discrete input register table is BOOL, and there are only two states: "0" and "1". Registers with 
smaller addresses are distributed in the lower bits of a byte storage area. For example, the eight registers reading addresses 
500 to 507 are stored in one byte during transmission. The lowest bit of this byte BIT0 stores the register value of address 500, 
and the highest bit BIT8 stores the register value of address 507. 
When the number of request registers is not a multiple of 8, the remaining bits in the last byte are all filled with "0". For example, 
when reading the 10 registers from 500 to 509, the actual values of the 10 registers are "1". The response data is FFH, 03H, 
regardless of the values of the six registers from addresses 510 to 515. Note that the PC cannot parse the remaining filled 
positions into 510~515 address values when parsing the response. 
 
 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Number of subsequent 
bytes 
len 
1 
BYTE 
len = 2×cnt 
Data 
data 
2×cnt 
UINT 
 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Number of subsequent 
bytes 
len 
1 
BYTE 
When the number of request registers is a multiple of 
8, len=cnt/8. Otherwise len=(cnt/8)+1. 
Data 
data 
Len 
BOOL 
 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 3 / 19 
2.3. Remote Adjustment Command 
2.3.1. Timing 41H 
Function code: 41H 
Request site: Monitor the background/EMS 
Target site: SBMU device object address" 
Table 2-7 Time calibration command sends data 
Field 
Bytes 
Type 
Range 
Length 
1 
BYTE 
= 7 
Year 
1 
BYTE 
0~37 
Month 
1 
BYTE 
1~12 
Day 
1 
BYTE 
1~31 
Hour 
1 
BYTE 
0~23 
Minute 
1 
BYTE 
1~59 
Millisecond 
2×1 
UINT 
0~59999 
Response: System time after setting 
Table 2-8 Time calibration command response data 
Field 
Bytes 
Type 
Range 
Length 
1 
BYTE 
= 7 
Year 
1 
BYTE 
0~37 
Month 
1 
BYTE 
1~12 
Day 
1 
BYTE 
1~31 
Hour 
1 
BYTE 
0~23 
Minute 
1 
BYTE 
1~59 
Millisecond 
2×1 
UINT 
0~59999 
2.3.2. Single Regulation Holding Register 06H 
Function Code: 06H 
Request: Monitor the background 
Table 2-9 Single regulation holding register command sends data 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Register address 
addr 
2×1 
UINT 
 
Value 
Val 
2×1 
UINT 
 
Response: 
Table 2-10 Single regulation holding register command response data 
 
 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Register address 
addr  
2×1 
UINT 
Same as Request 
Value 
val 
2×1 
UINT 
Same as Request 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 4 / 19 
2.3.3. Block Adjustment Holding Register 10H 
Function Code: 10H 
Request: Monitor the background 
Table 2-11 Block Adjustment Holding Register Command Sending Data 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Start Register address 
addr  
2×1 
UINT 
 
Register Number 
cnt  
2×1 
UINT 
<=120 
Length of Value 
len  
1 
BYTE 
len = 2×cnt 
Value 
val 
2×cnt 
UINT 
 
Response: 
Table 2-12 Single regulation holding register command response data 
2.4. Exception Response Mechanism 
In case of exception response, function code=received function code+80H, and data is one byte exception code. 
The exception code is the corresponding cause of the exception, as shown in Table 4-6-1: 
Table 2-13 Meaning of exception code 
Code 
Name 
Reason 
1 
Illegal function 
The function code in the request command is not allowed. The slave device 
may execute the request in the wrong state. 
2 
Illegal address 
The data address contained in the request data is not allowed. Especially when 
there is a combination of starting address and number of registers in the 
request command data. For the slave device with 100 registers, the request 
with offset 96 and length 4 will succeed, and the request with offset 96 and 
length 5 will generate exception code 02. 
3 
Illegal Value 
The value in the request data is not allowed. The length of the data may be 
incorrect, or the value of the data may exceed the valid range of a specific 
value. 
 
 
Field 
Symbol 
Bytes 
Data Type 
Remark 
Start Register address 
addr  
2×1 
UINT 
Same as Request 
Register Number 
cnt 
2×1 
UINT 
Same as Request 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 5 / 19 
2.5. Common Transaction Reference Definitions 
Combined with the daily experience of SBMU monitoring, the following common reference transaction definitions and 
corresponding "transaction processing identifiers" are provided. This section is not binding, and actual users can customize the 
meaning of transactions according to their own needs 
2.5.1. Common Transactions of SBMU Device Objects 
Table 2-14 Common transactions of SBMU equipment objects 
Name 
Code 
Remark 
Read Discrete 
1 
 
Read Input 
2 
 
Read parameters 
3 
 
Modify parameters 
4 
 
Note: Not all of these transactions will be utilized, and the specifics of the transactions may vary. 
2.5.2. Common Transactions of CBMU Device Objects 
Table 2-15 Common transaction table for CBMU objects 
Name 
Code 
Remark 
Read parameters 
0 
 
Read summary alarm 
1 
 
Read individual alarm 
2 
 
Read summary input register 
3 
 
Read unit voltage 1~400 information 
10 
 
Note: The transaction identifier can be defined by yourself. The above table is for reference only. 
 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 6 / 19 
3. Register Distribution 
3.1. SBMU Regisiter Distribution 
3.1.1. Discrete Input Register Table 
Table 3-1 Discrete input register table 
Name 
Start Address (Decimal) 
Total length 
System data information 
1 
80 
Rack 1 data information 
200 
88 
Rack 2 data information 
300 
88 
Rack 3 data information 
400 
88 
Rack 4 data information 
500 
88 
Rack 5 data information 
600 
88 
Rack 6 data information 
700 
88 
Rack 7 data information 
800 
88 
Rack 8 data information 
900 
88 
Rack 9 data information 
1000 
88 
Rack 10 data information 
1100 
88 
Rack 11 data information 
1200 
88 
Rack 12 data information 
1300 
88 
Rack 13 data information 
1400 
88 
Rack 14 data information 
1500 
88 
Rack 15 data information 
1600 
88 
Rack 16 data information 
1700 
88 
Rack 17 data information 
1800 
88 
Rack 18 data information 
1900 
88 
Rack 19 data information 
2000 
88 
Rack 20 data information 
2100 
88 
Table 3-2 Detail information of discrete input register table 
Field 
Start Address (Decimal) 
Remark 
Specific details of heap information: corresponding data can be called according to project conditions, not necessarily all. 
Summary of total voltage undervoltage slight alarm 
at each rack in the system 
1 
0 -- No alarm, 1 -- Alarm 
Summary of total voltage undervoltage medium 
alarm at each rack in the system 
2 
0 -- No alarm, 1 -- Alarm 
Summary of total voltage undervoltage serious alarm 
at each rack in the system 
3 
0 -- No alarm, 1 -- Alarm 
Summary of total voltage overvoltage slight alarm at 
each rack in the system 
4 
0 -- No alarm, 1 -- Alarm 
Summary of total voltage overvoltage medium alarm 
at each rack in the system 
5 
0 -- No alarm, 1 -- Alarm 
Summary of total voltage overvoltage serious alarm 
at each rack in the system 
6 
0 -- No alarm, 1 -- Alarm 
Summary of overcurrent slight alarm at each rack in 
the system 
7 
0 -- No alarm, 1 -- Alarm 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 7 / 19 
Summary of overcurrent medium alarm at each rack 
in the system 
8 
0 -- No alarm, 1 -- Alarm 
Summary of overcurrent serious alarm at each rack 
in the system 
9 
0 -- No alarm, 1 -- Alarm 
Summary of low insulation resistance slight alarm at 
each rack in the system 
10 
0 -- No alarm, 1 -- Alarm 
Summary of low insulation resistance medium alarm 
at each rack in the system 
11 
0 -- No alarm, 1 -- Alarm 
Summary of low insulation resistance serious alarm 
at each rack in the system 
12 
0 -- No alarm, 1 -- Alarm 
Summary of Module low temperature slight alarm at 
each rack in the system 
13 
0 -- No alarm, 1 -- Alarm 
Summary of Module Low temperature medium 
alarm at each rack in the system 
14 
0 -- No alarm, 1 -- Alarm 
Summary of Module low temperature serious alarm 
at each rack in the system 
15 
0 -- No alarm, 1 -- Alarm 
Summary of Module over temperature slight alarm 
at each rack in the system 
16 
0 -- No alarm, 1 -- Alarm 
Summary of Module over temperature medium 
alarm at each rack in the system 
17 
0 -- No alarm, 1 -- Alarm 
Summary of Module over temperature serious alarm 
at each rack in the system 
18 
0 -- No alarm, 1 -- Alarm 
Summary of Cell over voltage slight alarm in the 
system 
19 
0 -- No alarm, 1 -- Alarm 
Summary of Cell mver voltage medium alarm in the 
system 
20 
0 -- No alarm, 1 -- Alarm 
Summary of Cell over voltage serious alarm in the 
system 
21 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low voltage slight alarm in the 
system 
22 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low voltage medium alarm in the 
system 
23 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low voltage serious alarm at each 
rack in the system 
24 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential voltage slight alarm in 
the system 
25 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential voltage medium alarm 
in the system 
26 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential voltage serious alarm in 
the system 
27 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low temperature slight alarm in the 
system 
28 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low temperature medium alarm in 
the system 
29 
0 -- No alarm, 1 -- Alarm 
Summary of Cell low temperature serious alarm in 
the system 
30 
0 -- No alarm, 1 -- Alarm 
Summary of Cell over temperature slight alarm in the 
system 
31 
0 -- No alarm, 1 -- Alarm 
Summary of Cell over temperature medium alarm in 
the system 
 
32 
0 -- No alarm, 1 -- Alarm 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 8 / 19 
Summary of Cell over temperature serious alarm in 
the system 
33 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential temperature slight 
alarm in the system 
34 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential temperature medium 
alarm in the system 
35 
0 -- No alarm, 1 -- Alarm 
Summary of Cell differential temperature serious 
alarm in the system 
36 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC low slight alarm in the system 
37 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC low medium alarm in the 
system 
38 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC Low serious alarm in the 
system 
39 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC high slight alarm in the system 
40 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC high medium alarm in the 
system 
41 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOC high serious alarm in the 
system 
42 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH low slight alarm in the system 
43 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH low medium alarm in the 
system 
44 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH low serious alarm in the 
system 
45 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH high slight alarm in the system 
46 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH high medium alarm in the 
system 
47 
0 -- No alarm, 1 -- Alarm 
Summary of Cell SOH high serious alarm in the 
system 
48 
0 -- No alarm, 1 -- Alarm 
Summary of each CBMU lost communication in the 
system 
49 
0 -- No alarm, 1 -- Alarm 
Summary of each V-T measurement board lost 
communication in the system 
50 
0 -- No alarm, 1 -- Alarm 
Abnormal voltage of each rack in the System (the 
total Voltage difference between racks is greater 
than 20V) 
51 
0 -- No alarm, 1 -- Alarm 
Abnormal disconnection of contactor 
52 
0 -- No alarm, 1 -- Alarm 
Abnormal closing of contactor 
53 
0 -- No alarm, 1 -- Alarm 
Charging prohibited 
54 
0 -- No alarm, 1 -- Alarm 
Discharging prohibited 
55 
0 -- No alarm, 1 -- Alarm 
BMS system alarm summary 
56 
0 -- No alarm, 1 -- Alarm 
Summary of BMS system faults 
57 
0 -- No alarm, 1 -- Alarm 
Input IN0 (according to the actual project air 
conditioning, emergency stop or other hardware 
signals) 
58 
0 -- No alarm, 1 -- Alarm 
Input IN1 (according to the actual project air 
conditioning, emergency stop or other hardware 
signals) 
59 
0 -- No alarm, 1 -- Alarm 
Input IN2 (according to the actual project air 
conditioning, emergency stop or other hardware 
signals) 
60 
0 -- No alarm, 1 -- Alarm 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 9 / 19 
Input IN3 (according to the actual project air 
conditioning, emergency stop or other hardware 
signals) 
61 
0 -- No alarm, 1 -- Alarm 
Reserved 
62 
0 -- No alarm, 1 -- Alarm 
Reserved 
63 
0 -- No alarm, 1 -- Alarm 
Reserved 
64 
0 -- No alarm, 1 -- Alarm 
Reserved 
65 
0 -- No alarm, 1 -- Alarm 
Reserved 
66 
0 -- No alarm, 1 -- Alarm 
Reserved 
67 
0 -- No alarm, 1 -- Alarm 
Reserved 
68 
0 -- No alarm, 1 -- Alarm 
Reserved 
69 
0 -- No alarm, 1 -- Alarm 
Summary of terminal over temperature slight alarm 
in the System 
70 
0 -- No alarm, 1 -- Alarm 
Summary of terminal over temperature medium 
alarm in the System 
71 
0 -- No alarm, 1 -- Alarm 
Summary of terminal over temperature serious 
alarm in the System 
72 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage overvoltage slight alarm 
in the System 
73 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage overvoltage medium 
alarm in the System 
74 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage overvoltage serious 
alarm in the System 
75 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage undervoltage slight 
alarm in the System 
76 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage undervoltage medium 
alarm in the System 
77 
0 -- No alarm, 1 -- Alarm 
Summary of module voltage undervoltage serious 
alarm in the System 
78 
0 -- No alarm, 1 -- Alarm 
Cell Voltage acquisition fault 
79 
0 -- No alarm, 1 -- Alarm 
Cell Temperature acquisition fault 
80 
0 -- No alarm, 1 -- Alarm 
Specific details of Rack information: corresponding data can be called according to project conditions, not necessarily all. 
Rack N CBMU lost communication 
200 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage undervoltage slight alarm 
201 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage undervoltage medium alarm 
202 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage undervoltage serious alarm 
203 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage overvoltage slight alarm 
204 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage overvoltage medium alarm 
205 
0 -- No alarm, 1 -- Alarm 
Rack N total voltage overvoltage serious alarm 
206 
0 -- No alarm, 1 -- Alarm 
Rack N over current slight alarm 
207 
0 -- No alarm, 1 -- Alarm 
Rack N over current medium alarm 
208 
0 -- No alarm, 1 -- Alarm 
Rack N over current serious alarm 
209 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage undervoltage slight alarm 
210 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage undervoltage medium alarm 
211 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage undervoltage serious alarm 
212 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage overvoltage slight alarm 
213 
0 -- No alarm, 1 -- Alarm 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 10 / 19 
Rack N cell voltage overvoltage medium alarm 
214 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage overvoltage serious alarm 
215 
0 -- No alarm, 1 -- Alarm 
Rack N cell low temperature slight alarm 
216 
0 -- No alarm, 1 -- Alarm 
Rack N cell low temperature medium alarm 
217 
0 -- No alarm, 1 -- Alarm 
Rack N cell low temperature serious alarm 
218 
0 -- No alarm, 1 -- Alarm 
Rack N cell over temperature slight alarm 
219 
0 -- No alarm, 1 -- Alarm 
Rack N cell over temperature medium alarm 
220 
0 -- No alarm, 1 -- Alarm 
Rack N cell over temperature serious alarm 
221 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC low slight alarm 
222 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC low medium alarm 
223 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC low serious alarm 
224 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC high slight alarm 
225 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC high medium alarm 
226 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC high serious alarm 
227 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOH low slight alarm 
228 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC low medium alarm 
229 
0 -- No alarm, 1 -- Alarm 
Rack N cell SOC low serious alarm 
230 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage different slight alarm 
231 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage different medium alarm 
232 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage different serious alarm 
233 
0 -- No alarm, 1 -- Alarm 
Rack N cell temperature different slight alarm 
234 
0 -- No alarm, 1 -- Alarm 
Rack N cell temperature different medium alarm 
235 
0 -- No alarm, 1 -- Alarm 
Rack N cell temperature different serious alarm 
236 
0 -- No alarm, 1 -- Alarm 
Rack N V-T measurement board #1 lost 
Communication 
237 
0 -- No alarm, 1 -- Alarm 
 … 
… 
0 -- No alarm, 1 -- Alarm 
Rack N V-T measurement board #40 lost 
Communication 
276 
0 -- No alarm, 1 -- Alarm 
Rack N terminal temperature high slight alarm 
277 
0 -- No alarm, 1 -- Alarm 
Rack N terminal temperature high medium alarm 
278 
0 -- No alarm, 1 -- Alarm 
Rack N terminal temperature high serious alarm 
279 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage overvoltage slight alarm 
280 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage overvoltage medium alarm 
281 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage overvoltage serious alarm 
282 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage undervoltage slight alarm 
283 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage undervoltage medium alarm 
284 
0 -- No alarm, 1 -- Alarm 
Rack N module voltage undervoltage serious alarm 
285 
0 -- No alarm, 1 -- Alarm 
Rack N cell voltage acquisition fault 
286 
0 -- No alarm, 1 -- Alarm 
Rack N Cell temperature acquisition fault 
287 
0 -- No alarm, 1 -- Alarm 
 
 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 11 / 19 
3.1.2. Holding Register Table 
Table 3-3 Holding register table 
Field 
Start Address 
(Decimal) 
Type 
Remark 
Rack Number 
500 
UINT 
1~20 
System fault reset 
501 
UINT 
0: Do not reset 1: Reset other values: Invalid 
System power up and 
down control command 
503 
UINT 
Note: It is not used by default, and the reactor is powered 
on automatically after power supply. If necessary, please 
specify in the project docking stage 
0: No operation  
1: Power on  
2: Power off  
Other values: Invalid 
RTC-Year 
524 
UINT 
Resolution: 1 
Offset: 2000 
Data field:0~100 
RTC-Month 
525 
UINT 
data field:1~12 
RTC-Day 
526 
UINT 
data field:1~31 
RTC-Hour 
527 
UINT 
data field:0~23 
RTC-Minute 
528 
UINT 
data field:0~59 
RTC-Second 
529 
UINT 
data field:0~59 
Heartbeat 
530 
UINT 
data field:0~65535 
 
 
 
 
Project peripheral 
information 
1000~2000 
 
Item peripheral information is added to addresses from 
1000 to 2000. 
 
 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 12 / 19 
3.1.3. Input Register Table 
Table 3-4 Input register table 
Name 
Start Address (decimal) 
Total Length 
System data 
1 
47 
Rack 1 data 
100 
2991 
Rack 2 data 
3100 
2991 
Rack 3 data 
6100 
2991 
Rack 4 data 
9100 
2991 
Rack 5 data 
12100 
2991 
Rack 6 data 
15100 
2991 
Rack 7 data 
18100 
2991 
Rack 8 data 
21100 
2991 
Rack 9 data 
24100 
2991 
Rack 10 data 
27100 
2991 
Rack 11 data 
30100 
2991 
Rack 12 data 
33100 
2991 
Rack 13 data 
36100 
2991 
Rack 14 data 
39100 
2991 
Rack 15 data 
42100 
2991 
Rack 16 data 
45100 
2991 
Rack 17 data 
48100 
2991 
Rack 18 data 
51100 
2991 
Rack 19 data 
54100 
2991 
Rack 20 data 
57100 
2991 
Peripheral information 
61000 
47 
Table 3-5 Detail information of Input register table 
Field 
Start 
Address 
(Decimal) 
Type 
Remark 
Specific details of Rack information: corresponding data can be called according to project conditions, not necessarily all. 
System total Voltage 
2 
UINT 
0.1V/bit 
System current 
3 
UINT 
0.1A/bit, Offset: -3200.0A 
System SOC 
4 
UINT 
1%/bit 
System SOH 
5 
UINT 
1%/bit 
Maximum battery voltage 
6 
UINT 
0.001V/bit 
Rack No of maximum voltage 
7 
UINT 
1/bit 
Cell No of maximum voltage in the rack 
8 
UINT 
1/bit 
Minimum battery voltage 
9 
UINT 
0.001V/bit 
Rack No of minimum voltage 
10 
UINT 
1/bit 
Cell No of minimum voltage in the rack 
11 
UINT 
1/bit 
Maximum battery temperature 
12 
UINT 
1°C/bit, Offset: -40°C 
Rack No of maximum temperature 
13 
UINT 
1/bit 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 13 / 19 
Cell No of maximum temperature in the rack 
14 
UINT 
1/bit 
Minimum battery temperature 
15 
UINT 
1°C/bit, Offset: -40°C 
Rack No of maximum temperature battery 
rack 
16 
UINT 
1/bit 
Cell No of minimum temperature in the rack 
17 
UINT 
1/bit 
System accumulated charging capacity 
18 
UINT32 
0.1KWh/bit 
System accumulated discharging capacity 
20 
UINT32 
0.1KWh/bit 
System accumulated charge quantity for a 
single time 
22 
UINT32 
0.1KWh/bit 
System accumulated discharge quantity for a 
single time 
24 
UINT32 
0.1KWh/bit 
System rechargeable capacity 
26 
UINT32 
0.1KWh/bit 
System dischargeable capacity 
28 
UINT32 
0.1KWh/bit 
Available discharge time 
30 
UINT 
Min/bit 
Available charging time 
31 
UINT 
Min/bit 
Allowable maximum discharge power 
32 
UINT 
0.1KW/bit 
Allowable maximum charge power 
33 
UINT 
0.1KW/bit 
Allowable maximum discharge current 
34 
UINT 
0.1A/bit    
Allowable maximum charge current 
35 
UINT 
0.1A/bit   
Discharge times of the day 
36 
UINT 
1 time/bit 
charge times of the day 
37 
UINT 
1 time/bit 
Discharge quantity of the day 
38 
UINT32 
0.1kWh/bit 
Charge quantity of the day 
40 
UINT32 
0.1kWh/bit 
Operating temperature 
42 
UINT 
1°C/bit, offset: -40°C, system average 
temperature  
System Status 
43 
UINT 
0x00: initialization;  
0x01: charging; 
0x02: discharging; 
0x03: ready; 
0x05: charge prohibition; 
0x06: discharge prohibition; 
0x07: charging and discharging prohibition; 
0x08: Fault  
 
Supplimental description: 
Initialization - The relay is not closed during 
the system power-on self-test; 
Charging - After the relay is closed, the 
system detects charging current in all racks; 
Discharge -- After the relay is closed, the 
system detects discharge current in all racks; 
Ready: After the relay is closed, there is no 
charging or discharging; 
Charge prohibition: The relay is closed, the 
system does not charge, allow discharge; 
Discharge prohibition: The relay is closed and 
the system allows charging. Discharges are 
prohibited; 
Charging and discharging prohibition: The 
relay is closed, and the system cannot charge 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 14 / 19 
or discharge; 
Fault -- The system is seriously faulty and 
requires a high voltage alarm; 
BMS charge and discharge state 
44 
UINT 
0x00: Others; 
0x01: Discharge; 
0x02: Charge. 
System insulation resistance 
45 
UINT 
1KΩ/bit 
Note: Check before powering on, no check 
required after powering on. 
PCS and BMS communication fault 
46 
UINT 
0x01: communication loss 0x00: 
communication is normal 
EMS and BMS communication fault 
47 
UINT 
0x01: communication loss 0x00: 
communication is normal 
System cumulative charging time 
48 
UINT32 
Unit: second, resolution: 1 
System cumulative discharging time 
50 
UINT32 
Unit: second, resolution: 1 
Rack information details: Specific details can be summoned according to the project requirements; not necessarily all details 
need to be summoned. 
Rack N Status 
100 
UINT 
0x00: initial state; 
0x01: charging; 
0x02: discharging; 
0x03: ready; 
0x04: rack maintenance; 
0x05: charge prohibition; 
0x06: discharge prohibition; 
0x07: charging and discharging prohibited; 
0x08: fault; 
Rack N maximum allowable charging power 
101 
UINT 
Resolution: 0.1 Unit: KW 
Rack N maximum allowable discharging 
power 
102 
UINT 
Resolution: 0.1 Unit: KW 
Rack N maximum allowable charging voltage 
103 
UINT 
Resolution: 0.1 Unit: V 
Rack N maximum allowable discharging 
voltage 
104 
UINT 
Resolution: 0.1 Unit: V 
Rack N maximum allowable charging current 
105 
UINT 
Resolution: 0.1 Unit: A 
Rack N maximum allowable discharging 
current 
106 
UINT 
Resolution: 0.1 Unit: A 
 
 
 
 
Rack N total voltage 
115 
UINT 
0.1V/bit 
Rack N current 
116 
UINT 
0.1A/bit, offset: -3200.0A  
Rack N average temperature 
117 
UINT 
1°C/bit, offset: -40°C 
Rack N SOC 
118 
UINT 
1%/bit 
Rack N SOH 
119 
UINT 
1%/bit 
Rack N insulation resistance 
120 
UINT 
1KΩ/bit 
Rack N average cell voltage 
121 
UINT 
0.001V/bit 
Rack N average cell temperature 
122 
UINT 
1°C/bit, offset: -40°C 
Rack N maximum cell voltage 
123 
UINT 
0.001V/bit 
Cell No of maximum cell voltage in rack N 
124 
UINT 
1/bit 
Rack N minimum cell voltage 
125 
UINT 
0.001V/bit 
Cell No of minimum cell voltage in rack N 
126 
UINT 
1/bit 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 15 / 19 
Rack N maximum cell temperature 
127 
UINT 
1°C/bit, offset: -40°C 
Cell No of maximum temperature in rack N 
128 
UINT 
1/bit 
Rack N minimum cell temperature 
129 
UINT 
1°C/bit, offset: -40°C 
Cell No of minimum temperature in rack N 
130 
UINT 
1/bit 
Rack N maximum cell SOC 
131 
UINT 
1%/bit 
Cell No of maximum cell SOC in rack N 
132 
UINT 
1/bit 
Rack N minimum cell SOC 
133 
UINT 
1%/bit 
Cell No of minimum cell SOC in rack N 
134 
UINT 
1/bit 
Rack N maximum cell SOH 
135 
UINT 
1%/bit 
Cell No of maximum cell SOH in rack N 
136 
UINT 
1/bit 
Rack N minimum cell SOH 
137 
UINT 
1%/bit 
Cell No of minimum cell SOH in rack N 
138 
UINT 
1/bit 
Rack N accumulated charging capacity 
139 
UINT32 
0.1KWh/bit 
Rack N accumulated discharging capacity 
141 
UINT32 
0.1KWh/bit 
Rack N accumulated charge quantity for a 
single time 
143 
UINT32 
0.1KWh/bit 
Rack accumulated discharge quantity for a 
single time 
145 
UINT32 
0.1KWh/bit 
Rack N rechargeable capacity 
147 
UINT32 
0.1KWh/bit 
Rack N discharge capacity 
149 
UINT32 
0.1KWh/bit 
Rack N module 1 SOC 
151 
UINT 
1%/bit 
… 
 
UINT 
1%/bit 
Rack N module 40 SOC 
190 
UINT 
1%/bit 
Rack N cell voltage 001 
191 
UINT 
0.001V/bit 
… 
 
UINT 
0.001V/bit 
Rack N cell voltage 700 
890 
UINT 
0.001V/bit  
Rack N cell temperature 001 
891 
UINT 
1°C/bit, offset: -40°C 
… 
 
UINT 
1°C/bit, offset: -40°C 
Rack N cell temperature 700 
1590 
UINT 
1°C/bit, offset: -40°C 
Rack N cell SOC 001 
1591 
UINT 
1%/bit 
… 
 
UINT 
1%/bit 
Rack N cell SOC 700 
2290 
UINT 
1%/bit 
Rack N cell SOH 001 
2291 
UINT 
1%/bit 
… 
 
UINT 
1%/bit 
Rack N cell SOH 700 
2990 
UINT 
1%/bit 
Rack N terminal temperature 001 
2991 
UINT 
1°C/bit, offset: -40°C 
… 
 
 
 
Rack N terminal temperature 100 
3090 
UINT 
1°C/bit, offset: -40°C 
Peripheral information 
TMS operational status (Liquid cooling unit) 
60100 
UINT 
0: OFF mode; 
1: Cooling mode; 
2: Heating mode; 
3: Auto cycle mode. 
K1 relay status 
60101 
UINT 
0: Opend status; 
1: Closing status; 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 16 / 19 
2~3: Invalid. 
K2 relay status 
60102 
UINT 
0: Opend status; 
1: Closing status; 
2~3: Invalid. 
Preheat mode feedback 
60103 
UINT 
0: Exit preheat mode; 
1: Enter preheat mode; 
2~3: Invalid. 
Outlet temperature 
60104 
UINT 
Resolutions: 1°C/bit  
Offset: -40°C 
Range: -40°C~210°C 
Unit: °C 
Type: test 
255: Invalid value 
Return temperature 
60105 
UINT 
Resolutions: 1°C/bit  
Offset: -40°C 
Range: -40°C~210°C 
Unit: °C 
Type: test 
255: Invalid value 
Ambient temperature 
60106 
UINT 
Resolutions: 1°C/bit  
Offset: -40°C 
Range: -40°C~210°C 
Unit: °C 
Type: test 
255: Invalid value 
Inlet pressure value 
60107 
UINT 
Resolutions: 0.1bar/bit 
Offset: 0 
Unit: bar 
Range: 0bar~25.0bar 
255: Invalid value 
Outlet pressure value 
60108 
UINT 
Resolutions: 0.1bar/bit 
Offset: 0 
Unit: bar 
Range: 0bar~25.0bar 
255: Invalid value 
Ambient humidity 
60109 
UINT 
Resolutions: 1%/bit 
Offset: 0 
Unit: % 
Range: 0%~100% 
255: Invalid value 
TMS fault code 
60110 
UINT 
0: No fault. 
For other specific fault codes, please refer to 
the TMS Communication Protocol Fault Code 
Table. 
TMS fault leve 
60111 
UINT 
0: No fault; 
1: Alarm I; 
2: Alarm II. 
ACDC_A voltage 
60112 
UINT 
Resolutions: 1V/bit 
Offset: 0 
Unit: V 
Range: 0-32V 
Water pump PWM 
60113 
UINT 
Resolutions: 1%/bit 
Offset: 0 
Unit: %  

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 17 / 19 
Range: 0-100% 
255: Invalid value 
HV value 
60114 
UINT 
Resolutions: 1KPa/bit 
Offset: 0 
Unit: KPa 
Range: 0-3400KPa 
LV value 
60115 
UINT 
Resolutions: 1KPa/bit 
Offset: 0 
Unit: KPa 
Range: 0-3200KPa 
Fan PWM 
60116 
UINT 
Resolutions: 1%/bit 
Offset: 0 
Unit: %  
Range: 0-100% 
255: Invalid value 
Electronic expansion valve opening 
60117 
UINT 
Resolutions: 2step/bit 
Offset: 0 
Unit: step 
Range: 0-250% 
255: Invalid value 
Compressor voltage 
60118 
UINT 
Resolutions: 3V/bit 
Offset: 0 
Unit: V 
Range: 0-765V 
Compressor speed 
60119 
UINT 
Resolutions: 100rpm/bit 
Offset: 0 
Unit: rpm 
Range: 0-200 
255: Invalid value 
PTC temperature switch status 
60120 
UINT 
0: Opend status; 
1: Closing status; 
Dehumidification status (Pump switch) 
60121 
UINT 
0: Opend status; 
1: Closing status; 
AC fault 
60122 
UINT 
00: No fault. 
Reserved 
60123 
UINT 
0.1°C 
Reserved 
60124 
UINT 
0.1%RH 
Meter operating time (Meter) 
60125 
UINT 
0.01 
Maximum/average forward active power 
60126 
UINT 
10 
Apparent power 
60127 
UINT 
10 
Reserved 
60128 
UINT 
10 
Phase A voltage 
60129 
UINT 
0.01 
Phase B voltage 
60130 
UINT 
0.01 
Phase C voltage 
60131 
UINT 
0.01 
Phase A current 
60132 
UINT 
0.001 
Phase B current 
60133 
UINT 
0.001 
Phase C current 
60134 
UINT 
0.001 
Frequency 
60135 
UINT 
0.01 
Phase A active power 
60136 
UINT 
10 
Phase B active power 
60137 
UINT 
10 
Phase C active power 
60138 
UINT 
10 
Active power 
60139 
UINT 
10 
Reactive power 
60140 
UINT 
10 

 
ESS_5016&4180kWh_BMS Communication Protocol with EMS via Modbus_V1.6 
Confidential 
 
 
 18 / 19 
Self-check status (UPS) 
60141 
UINT 
 
Self-check feedback 
60142 
UINT 
 
Auxiliary power supply status 
60143 
UINT 
 
UPS output status 
60144 
UINT 
 
Load status 
60145 
UINT 
 
Charging/discharging status 
60146 
UINT 
 
Battery remaining capacity 
60147 
UINT 
Unit: % 
Battery remaining time (seconds) 
60148 
UINT 
Unit: s 
Auxiliary power supply abnormality 
60149 
UINT 
 
Feedback of circuit breaker (DI) 
60150 
UINT 
 
Container access control 
60151 
UINT 
 
PCS emergency stop 
60152 
UINT 
 
SPD feedback 2 
60153 
UINT 
 
Flood 
60154 
UINT 
 
Combustible gas alarm 
60155 
UINT 
 
Explosion-proof fan status 
60156 
UINT 
 
Explosion-proof fan alarm  
60157 
UINT 
 
Container emergency stop (restart to release) 
60158 
UINT 
 
Fire protection fault 
60159 
UINT 
 
Fire protection alarm (level I) 
60160 
UINT 
 
Fire protection alarm (level II) 
60161 
UINT 
 
AC detection 
60162 
UINT 
 
Forward active energy 
60163 
UINT 
1000 
Forward reactive energy 
60164 
UINT 
1000 
BMS request mode (Liquid cooling unit)   
60165 
UINT 
0: OFF mode; 
1: Cooling mode; 
2: Heating mode; 
3: Auto cycle mode. 
BMS status  
60166 
UINT 
0: Automatic mode 
1: BMS control 
Set temperature 
60167 
UINT 
Resolutions: 1°C/bit 
Offset: -40°C 
Unit: °C 

 
 
 
 
 
All rights reserved. Subject to change without notice. 
 
Xiamen Hithium Energy Storage Technology Co., Ltd. 
HiTHIUM Industrial Park, Tongxiang High Tech Zone, Xiamen, Fujian, China  
T: +86 0592-5513735 
E: hithium@hithium.cn 
Web: www.hithium.com 
 
 
  
 19 / 19 
 

