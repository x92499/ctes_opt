# Curve Equation Calculator
# Karl Heine, Nov 11, 2020

def BiQuad(c, x, y):

    result = c[0] + c[1]*x + c[2]*(x**2) + c[3]*y + c[4]*(y**2) + c[5]*x*y

    return result

def Quad(c, x):

    result = c[0] + c[1]*x + c[2]*x**2

    return result

def QuadLin(c, x, y):

    result = c[0] + c[1]*x + c[2]*(x**2) + (c[3] + c[4]*x + c[5]*(x**2))*y

    return result

def Poly5(c, x):

    result = c[0] + c[1]*x + c[2]*(x**2) + c[3]*(x**3) + c[4]*(x**4) + c[5]*(x**5)

    return result
