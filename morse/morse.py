import RPi.GPIO as GPIO
import time

# Morse morse_cording_durations
# Farnsworth Timing
time_unit = 0.1
morse_cording_durations = {
    '.': time_unit,
    '-': time_unit*3,
    'sleep': time_unit,
    'word_sleep': time_unit*7,
    'done': time_unit*10
}

# Alphabet
morse_cording = {'A': ['.', '-'],               'B': ['-', '.', '.', '.'],      'C': ['-', '.', '-', '.'],
                 'D': ['-', '.', '.'],          'E': ['.'],                     'F': ['.', '.', '-', '.'],
                 'G': ['-', '-', '.'],          'H': ['.', '.', '.', '.'],      'I': ['.', '.'],
                 'J': ['.', '-', '-', '-'],     'K': ['-', '.', '-'],           'L': ['.', '-', '.', '.'],
                 'M': ['-', '-'],               'N': ['-', '.'],                'O': ['-', '-', '-'],
                 'P': ['.', '-', '-', '.'],     'Q': ['-', '-', '.', '-'],      'R': ['.', '-', '.'],
                 'S': ['.', '.', '.'],          'T': ['-'],                     'U': ['.', '.', '-'],
                 'V': ['.', '.', '.', '-'],     'W': ['.', '-', '-'],           'X': ['-', '.', '.', '-'],
                 'Y': ['-', '.', '-', '-'],     'Z': ['-', '-', '.', '.'],

                 '0': ['-', '-', '-', '-', '-'],  '1': ['.', '-', '-', '-', '-'],  '2': ['.', '.', '-', '-', '-'],
                 '3': ['.', '.', '.', '-', '-'],  '4': ['.', '.', '.', '.', '-'],  '5': ['.', '.', '.', '.', '.'],
                 '6': ['-', '.', '.', '.', '.'],  '7': ['-', '-', '.', '.', '.'],  '8': ['-', '-', '-', '.', '.'],
                 '9': ['-', '-', '-', '-', '.']
                 }

# Ports
MAIN_LED = 12
DONE_LED = 26


def translate_morse(msg: str) -> list:
    cmds = []
    for s in msg:
        snd = 0
        slp = 0
        if s == ' ':
            # Word break
            slp = morse_cording_durations['word_sleep']
            cmds.append((0, slp))
            continue

        if s.upper() not in morse_cording:
            print('{} skipped'.format(s))
            continue

        cmd = morse_cording[s.upper()]
        print('{} -> {}'.format(s, cmd))
        for c in cmd:
            snd = morse_cording_durations[c]
            # + Wait
            slp = morse_cording_durations['sleep']
            # Add instruction
            cmds.append((snd, slp))
    return cmds


def setup(*leds):
    for led in leds:
        GPIO.setup(led, GPIO.OUT)


def teardown(*leds):
    for led in leds:
        GPIO.output(led, GPIO.LOW)


def send_msg(data: list, led=12, done_led=26):
    GPIO.setmode(GPIO.BCM)
    setup(led, done_led)
    for i in data:
        snd, slp = i
        print('Sending: {}, Waiting: {}'.format(snd, slp))
        # On
        GPIO.output(led, GPIO.HIGH)
        time.sleep(snd)
        GPIO.output(led, GPIO.LOW)
        # Sleep
        time.sleep(slp)
    print('Done sending message!')
    GPIO.output(done_led, GPIO.HIGH)
    time.sleep(morse_cording_durations['done'])
    GPIO.output(done_led, GPIO.LOW)


GPIO.setwarnings(False)

in_msg = input('Message: ')
msg = translate_morse(in_msg)
send_msg(msg)

# Turn off afterwards
teardown(MAIN_LED, DONE_LED)
