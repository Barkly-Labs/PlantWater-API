# carriers.py
from enum import Enum

class Carrier(str, Enum):
    verizon = "verizon"
    tmobile = "tmobile"
    att = "att"
    mint = "mint"
    rogers = "rogers"
    sprint = "sprint"