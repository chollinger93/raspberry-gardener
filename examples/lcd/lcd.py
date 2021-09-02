import i2clcd
import time 
import psutil
from gpiozero import CPUTemperature

def top(lcd):
    # gives a single float value
    cpu = '{:.2f}'.format(psutil.cpu_percent())
    mem = '{:.2f}'.format(psutil.virtual_memory().percent)
    temp = '{:.2f}'.format(CPUTemperature().temperature)
    lcd.print_line(f'{cpu}%CPU|{mem}%', line=0)
    lcd.print_line(f'Mem|{temp}C', line=1)

    time.sleep(2)

def cel(lcd):
    # custom character
    char_celsius = (0x10, 0x06, 0x09, 0x08, 0x08, 0x09, 0x06, 0x00)
    lcd.write_CGRAM(char_celsius, 0)
    lcd.move_cursor(0, 6)
    lcd.print(b'CGRAM: ' + i2clcd.CGRAM_CHR[0])
    time.sleep(5)

lcd = i2clcd.i2clcd(i2c_bus=1, i2c_addr=0x27, lcd_width=16)
lcd.init()

# fill a line by the text
lcd.clear()
while True:
    top(lcd)
#lcd.print_line('hello', line=0)
#lcd.print_line('world!', line=1, align='RIGHT')

#time.sleep(5)

# print text at the current cursor position
#lcd.move_cursor(1, 0)
#lcd.print('the')



