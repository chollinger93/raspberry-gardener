import SI1145.SI1145 as SI1145

#baseline=260
baseline=0

sensor = SI1145.SI1145()
vis = sensor.readVisible() - baseline
IR = sensor.readIR() - baseline
UV = sensor.readUV() 
uvIndex = UV / 100.0
print('Visible:  {}'.format(vis))
print('IR:       {}'.format(IR))
print('UV Index: {}'.format(uvIndex))
