#pragma version 8

const int I = 123
const bytes B = "abc"
const bigint Bi = 1231231231231231231231231231231231 
const bigint One = 1
assert((Bi / Bi) == One)

exit(1)