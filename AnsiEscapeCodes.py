# coding=utf-8

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#            Esse script faz parte de um projeto bem maior, solto no momento pq quero feedback, de tudo.              #
#         Também preciso que ele seja testado contra diversos cursos e que os problemas sejam apresentados.           #
#                                          Meu telegram: @katomaro                                                    #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class Colors:
    """ANSI Escape codes for the console output with colors and rich text.

    How to use: print(f"Total errors this run: {Cores.Red if a > 0 else Cores.Green}{a}")
    Read more also: 
        * https://en.wikipedia.org/wiki/ANSI_escape_code
        * https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html
        * https://gist.github.com/arlm/f624561b2cd3f53cb26112f3e48f97cd
        * https://www.ecma-international.org/publications-and-standards/standards/ecma-48/

    Attributes:
        Reset (str): Reset colors.
        Bold (str): Makes text bold.
        Underline (str): Underlines text.
        Red (str): Red foreground text.
        Green (str): Green foreground text.
        Yellow (str): Yellow foreground text.
        Blue (str): Blue foreground text.
        Magenta (str): Magenta foreground text.
        Cyan (str): Cyan foreground text.
        bgRed (str): Red background.
        bgGreen (str): Green background.
        bgYellow (str): Yellow background.
        bgBlue (str): Blue background.
        bgMagenta (str): Magenta background.
        bgCyan (str): Cyan background.
        bgWhite (str): White background.
    """
    
    Reset = '\u001b[0m'
    """Reset colors ANSI Escape code.
    """
    Bold = '\u001b[1m'
    """Makes text bold ANSI Escape code.
    """
    Underline = '\u001b[4m'
    """Underlines text ANSI Escape code.
    """

    Red = '\u001b[31m'
    """Red foreground text ANSI Escape code.
    """
    Green = '\u001b[32m'
    """Green foreground text ANSI Escape code.
    """
    Yellow = '\u001b[33m'
    """Yellow foreground text ANSI Escape code.
    """
    Blue = '\u001b[34m'
    """Blue foreground text ANSI Escape code.
    """
    Magenta = '\u001b[35m'
    """Magenta foreground text ANSI Escape code.
    """
    Cyan = '\u001b[36m'
    """Cyan foreground text ANSI Escape code.
    """

    bgRed = '\u001b[41m'
    """Red background ANSI Escape code.
    """
    bgGreen = '\u001b[42m'
    """Green background ANSI Escape code.
    """
    bgYellow = '\u001b[43m'
    """Yellow background ANSI Escape code.
    """
    bgBlue = '\u001b[44m'
    """Blue background ANSI Escape code.
    """
    bgMagenta = '\u001b[45m'
    """Magenta background ANSI Escape code.
    """
    bgCyan = '\u001b[46m'
    """Cyan background ANSI Escape code.
    """
    bgWhite = '\u001b[47m'
    """White background ANSI Escape code.
    """