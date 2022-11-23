const int MAX_INT_64 = 18446744073709551615

# a and b are very big numbers and multiplication of them doesn't fit in to uint 64.
int a = MAX_INT_64
int b = MAX_INT_64 / 2

bytes mul = itob(a) b* itob(b)
bytes sum = itob(a) b+ itob(b)
int result = btoi(mul b/ sum)