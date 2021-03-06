__author__ = 'Tirth Patel <complaints@tirthpatel.com>'

import pybot
from requests import get as req
from re import findall
from json import loads
from random import shuffle

delimiter = ' '


class Clue:
    def __init__(self, number, coords, direction, clue, length, answer=None):
        self.number = number
        self.direction = direction
        self.row, self.col = coords[0], coords[1]
        self.clue = clue
        self.answers = [answer] if answer else None
        self.length = length

    def __repr__(self):
        return ('{0} {1} {2} - {3} ({4}): {5}'
                .format(str(self.number), self.direction, (self.row, self.col),
                        self.clue, str(self.length), self.answers))

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False


def gen_guardian_clue(given, direction):
    clue_num = int(given[0])
    coords = coord(given[1])
    clue = ' '.join(given[2:])
    clue_len = sum([int(i) for i in given[-1][1:-1].replace('-', ',').split(',')])

    return Clue(clue_num, coords, direction, clue, clue_len)


class Crossword:
    def __init__(self, size=13, across=None, down=None, answers=None):
        self.size = size
        self.puzzle = [[delimiter for _ in range(size)] for _ in range(size)]
        self.clues, self.answers = [], []
        self.given_ans = None

        if across and down:
            self.fill_clues(across, down)
            self.first_clue = self.clues[0]

        if answers:
            with open(answers, 'r') as ans:
                self.given_ans = loads(ans.read())

    def fill_clues(self, across, down, reset=False):
        if reset:
            self.puzzle = [[delimiter for _ in range(self.size)]
                           for _ in range(self.size)]
            shuffle(self.clues)
        else:
            across_keys = sorted(across.keys())
            down_keys = sorted(down.keys())

            a_index, d_index = 0, 0
            for i in range((max(len(across), len(down)))):
                if a_index < len(across):
                    self.clues.append(across[across_keys[a_index]])
                    a_index += 1

                if d_index < len(down):
                    self.clues.append(down[down_keys[d_index]])
                    d_index += 1

    def fill_answers(self):
        counter = 0
        a_ans, d_ans = [], []

        for clue in self.clues:
            clue.answers = (self.given_ans[clue.clue] if self.given_ans
                            else get_answers(clue))

            counter += 1
            print(str(counter * 100 // len(self.clues)) + '%')

            if len(clue.answers) == 0:
                print(clue, 'no answers found :(')
                continue

            collision = False

            for answer in clue.answers:
                current_word = ''
                for i in range(clue.length):
                    current_word += (self.puzzle[clue.row][clue.col + i]
                                     if clue.direction == 'across'
                                     else self.puzzle[clue.row + i][clue.col])

                    if current_word[i] != delimiter and answer[1][i] != \
                            current_word[i]:
                        collision = True
                        break

                if collision:  # try another answer
                    if clue.answers.index(answer) == len(clue.answers) - 1:
                        print('bummer', clue)  # no more answers left
                        return False
                    collision = False
                    continue

                a_ans.append((clue.number, answer[1])) \
                    if clue.direction == 'across' \
                    else d_ans.append((clue.number, answer[1]))

                for i in range(clue.length):
                    if clue.direction == 'across':
                        self.puzzle[clue.row][clue.col + i] = answer[1][i]
                    elif clue.direction == 'down':
                        self.puzzle[clue.row + i][clue.col] = answer[1][i]
                break

        # sort by clue number for entry into puzzle
        self.answers = ([a[1] for a in sorted(a_ans, key=lambda a: a[0])] +
                        [a[1] for a in sorted(d_ans, key=lambda a: a[0])])
        return True

    def __str__(self):
        s = ''
        for i in range(self.size):
            for j in range(self.size):
                s += str(self.puzzle[i][j]) + ' '
            s += '\n'  # + '-' * self.size * 2 + '\n'

        return s


def get_guardian(number):
    across, down = {}, {}

    r = req('http://www.theguardian.com/crosswords/quick/' + number + '/blind')

    if r.status_code != 200:
        raise PuzzleNotFound()

    resp = ' '.join(r.text.split())

    acr = findall(r'<li>(.*?) </li>', findall(r'<h2>Across(.*?)</u', resp)[0])
    dow = findall(r'<li>(.*?) </li>', findall(r'<h2>Down(.*?)</ul>', resp)[0])

    # build Clue objects from given puzzle
    for a in acr:
        clue = a.strip().split()
        across[int(clue[0])] = gen_guardian_clue(clue, 'across')

    for d in dow:
        clue = d.strip().split()
        down[int(clue[0])] = gen_guardian_clue(clue, 'down')

    return across, down


class PuzzleNotFound(LookupError):
    pass


def read_guardian_puzzle(file):
    across, down = {}, {}
    with open(file, 'r') as puzzle:
        puzz = puzzle.readlines()

    switch = puzz.index('\n')

    for i in range(len(puzz)):
        p = puzz[i].strip().split()

        if i < switch:
            across[int(p[0])] = gen_guardian_clue(p, 'across')
        elif i > switch:
            down[int(p[0])] = gen_guardian_clue(p, 'down')

    return across, down


def get_answers(clue_in):
    if clue_in.answers is None:
        url = 'http://www.wordplays.com/crossword-solver/'

        # encode URL
        for c in clue_in.clue:
            if c == ' ':
                url += '-'
            elif c == ',':
                url += '%2C'
            elif c == ':':
                url += '%3A'
            elif c == '?':
                url += '%3F'
            elif c == '\'':
                url += '%27'
            elif c == '(':
                url += '%28'
            elif c == ')':
                url += '%29'
            else:
                url += c

        pybot.chill_out_for_a_bit(3)  # don't send requests too quickly
        r = req(url)

        if r.status_code != 200:
            print('Nope', url)

        # get ranks and answers
        scraped = findall(r'class=stars>(.*?)<td class=clue', r.text)

        # clean up and put into list
        answers = []
        for clue in scraped:
            stars = len(findall(r'<div></div>', clue))
            ans = findall(r'crossword-clues/(.*?)"', clue)[0].strip().lower()
            if len(ans) == clue_in.length:
                answers.append((stars, ans))

        return answers
    else:
        return clue_in.answers


# alphanumeric to coordinate conversion ex. (2B) -> (1, 1)
def coord(c):
    if len(c) == 4:
        return int(c[1]) - 1, ord(c[2]) - ord('A')
    elif len(c) == 5:
        return int(c[1:3]) - 1, ord(c[3]) - ord('A')


if __name__ == '__main__':
    pass
