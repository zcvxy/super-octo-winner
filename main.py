#!/usr/bin/env python
# -*- coding: latin-1 -*-
import csv
import yaml
import random
import atexit
import codecs

from typing import *
from os.path import join
from psychopy import visual, event, logging, gui, core


@atexit.register
def save_beh_results() -> None:
    """
    Save results of experiment. Decorated with @atexit in order to make sure, that intermediate
    results will be saved even if interpreter will break.

    Returns:
        Nothing.
    """
    file_name = PART_ID + '_' + str(random.choice(range(100, 1000))) + '_beh.csv'
    with open(join('results', file_name), 'w', encoding='utf-8') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()


def show_image(win: visual.window, file_name: str, size: List[int], key: str = 'f7') -> None:
    """
    Show instructions in a form of an image.
    Args:
        win:
        file_name: Img file.
        size: Img size [width, height].
        key: Key to terminate procedure.

    Returns:
        Nothing.
    """
    image = visual.ImageStim(win=win, image=file_name, interpolate=True, size=size)
    image.draw()
    win.flip()
    clicked = event.waitKeys(keyList=[key, 'return', 'space'])
    if clicked == [key]:
        logging.critical('Experiment finished by user! {} pressed.'.format(key[0]))
        exit(0)
    win.flip()


def read_text_from_file(file_name: str, insert: str = '') -> str:
    """
    Method that read message from text file, and optionally add some
    dynamically generated info.
    Args:
        file_name: Name of file to read
        insert:

    Returns:
        String to display.
    """
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit(key: str = 'f7') -> None:
    """
    Check if exit button pressed.

    Returns:
        Nothing.
    """
    stop = event.getKeys(keyList=[key])
    if stop:
        abort_with_error('Experiment finished by user! {} pressed.'.format(key))


def show_info(win: visual.Window, file_name: str, insert: str = '') -> None:
    """
    Clear way to show info message into screen.
    Args:
        win:
        file_name:
        insert:

    Returns:
        Nothing.
    """
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color='black', text=msg, height=30, wrapWidth=SCREEN_RES[0])
    msg.draw()
    win.flip()
    key = event.waitKeys(keyList=['esc', 'return', 'space', 'left', 'right'])
    if key == ['f7']:
        abort_with_error('Experiment finished by user on info screen! F7 pressed.')
    win.flip()


def abort_with_error(err: str) -> None:
    """
    Call if an error occurred.

    Returns:
        Nothing.
    """
    logging.critical(err)
    raise Exception(err)


# GLOBALS

RESULTS = list()  # list in which data will be colected
# ... Results header
RESULTS.append(['id', 'type', 'central_char', 'surrounding_char', 'trial_number', 'trial_type', 'key_pressed', 'correct', 'reaction_time'])
SCREEN_RES = []


def main():
    global PART_ID  # PART_ID is used in case of error on @atexit, that's why it must be global

    # === Dialog popup ===
    info: Dict = {'ID': '', 'Sex': ['M', "F"], 'Age': ''}
    dict_dlg = gui.DlgFromDict(dictionary=info, title='Experiment title, fill by your name!')
    if not dict_dlg.OK:
        abort_with_error('Info dialog terminated.')

    # load config, all params should be there
    conf: Dict = yaml.load(open('config.yaml', encoding='utf-8'), Loader=yaml.SafeLoader)
    global SCREEN_RES
    SCREEN_RES = conf['SCREEN_RES']
    # === Scene init ===
    win = visual.Window(SCREEN_RES, fullscr=False, monitor='testMonitor', units='pix', color=conf['BACKGROUND_COLOR'])
    event.Mouse(visible=False, newPos=None, win=win)  # Make mouse invisible

    PART_ID = info['ID'] + info['Sex'] + info['Age']
    logging.LogFile(join('results', f'{PART_ID}.log'), level=logging.INFO)  # errors logging
    logging.info('SCREEN RES: {}'.format(SCREEN_RES))

    # === Training ===
    show_info(win, join('.', 'messages', 'hello.txt'))
    show_info(win, join('.', 'messages', 'before_training.txt'))
    run_session(win, conf, conf['NO_TRAINING_TRIALS'], True)

    # === Experiment ===
    show_info(win, join('.', 'messages', 'before_experiment.txt'))

    for block_no in range(conf['NO_BLOCKS']):
        run_session(win, conf, conf['TRIALS_IN_BLOCK'], False)
        #break
        if block_no == 0:
            show_info(win, join('.', 'messages', 'break.txt'))
    # === Cleaning time ===
    save_beh_results()
    logging.flush()
    show_info(win, join('.', 'messages', 'end.txt'))
    win.close()


def run_session(win, conf, no_trials, is_training):
    for trial_no in range(no_trials):
        key_pressed, rt, central, surrounding = run_trial(win, conf)
        corr = central == key_pressed
        typ = "Zgodny" if central == surrounding else "Neutralny" if surrounding == 'o' else "Niezgodny"
        RESULTS.append([PART_ID, typ, central, surrounding, trial_no, 'training' if is_training else "experimental", key_pressed, str(corr), rt])
        # it's a good idea to show feedback during training trials
        if is_training:
            feedb = "Poprawnie" if corr else "Niepoprawnie"
            feedb = visual.TextStim(win, text=feedb, height=conf['TEXT_HEIGHT'], color=conf['FIX_CROSS_COLOR'])
            feedb.draw()
            win.flip()
            core.wait(1)


def run_trial(win, conf):
    """
    Prepare and present single trial of procedure.
    Input (params) should consist all data need for presenting stimuli.
    If some stimulus (eg. text, label, button) will be presented across many trials.
    Should be prepared outside this function and passed for .draw() or .setAutoDraw().
    Returns:
        All behavioral data (reaction time, answer, etc. should be returned from this function).
    """

    # === Prepare trial-related stimulus ===
    central = random.choice(['left', 'right'])
    surrounding = random.choice(['left', 'right', 'neutral'])
    central_char = '<' if central == 'left' else '>'
    surrounding_char = '<' if surrounding == 'left' else '>' if surrounding == 'right' else 'o'
    text = 2 * surrounding_char + central_char + 2 * surrounding_char
    stim = visual.TextStim(win, text=text, color='black', height=conf['TEXT_HEIGHT'])
    # === Start pre-trial  stuff (Fixation cross etc.)===
    fix_cross = visual.TextStim(win, text='x', color='black', height=conf['TEXT_HEIGHT']-15)
    fix_cross.draw()
    win.flip()
    core.wait(conf['FIX_CROSS_TIME_S'])

    # === Start trial ===
    # This part is time-crucial. All stims must be already prepared.

    # Only .draw() .flip() and reaction related stuff goes there.
    event.clearEvents()
    clock = core.Clock()
    reaction = None
    stim.draw()
    win.flip()
    while clock.getTime() < conf['STIM_TIME_S']:
        reaction = event.getKeys(keyList=list(conf['REACTION_KEYS']), timeStamped=clock)
        if reaction:  # break if any button was pressed
            break

    # === Trial ended, prepare data for send  ===
    if reaction:
        key_pressed, rt = reaction[0]
    else:  # timeout
        key_pressed = 'no_key'
        rt = -1.0

    # id, type, central, surrounding, trial_number, key_pressed, corr, rt
    return key_pressed, rt, central, surrounding  # return all data collected during trial


if __name__ == '__main__':
    PART_ID = ''
    main()
