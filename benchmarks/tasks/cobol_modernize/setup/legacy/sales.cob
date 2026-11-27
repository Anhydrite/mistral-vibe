       IDENTIFICATION DIVISION.
       PROGRAM-ID. SALES.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT SALES-FILE ASSIGN TO WS-PATH
               ORGANIZATION IS LINE SEQUENTIAL.
       DATA DIVISION.
       FILE SECTION.
       FD SALES-FILE.
       01 SALES-REC          PIC X(80).
       WORKING-STORAGE SECTION.
       01 WS-PATH            PIC X(120).
       01 WS-REGION          PIC X(12).
       01 WS-ITEM            PIC X(12).
       01 WS-QTY-TEXT        PIC X(8).
       01 WS-PRICE-TEXT      PIC X(12).
       01 WS-QTY             PIC 9(4).
       01 WS-PRICE           PIC 9(5)V99.
       01 WS-AMOUNT          PIC 9(7)V99.
       01 WS-CUR-REGION      PIC X(12) VALUE SPACES.
       01 WS-FIRST           PIC X VALUE 'Y'.
       01 WS-EOF             PIC X VALUE 'N'.
       01 WS-REG-TOTAL       PIC 9(7)V99 VALUE ZERO.
       01 WS-GRAND           PIC 9(7)V99 VALUE ZERO.
       01 WS-TAX             PIC 9(7)V99 VALUE ZERO.
       01 WS-TOTAL           PIC 9(7)V99 VALUE ZERO.
       01 OUT-QTY            PIC ZZZ9.
       01 OUT-AMOUNT         PIC ZZZZZZ9.99.
       01 OUT-TOTAL          PIC ZZZZZZ9.99.
       PROCEDURE DIVISION.
           ACCEPT WS-PATH FROM COMMAND-LINE
           OPEN INPUT SALES-FILE
           DISPLAY 'ITEM         QTY   EXTENDED'
           PERFORM UNTIL WS-EOF = 'Y'
               READ SALES-FILE INTO SALES-REC
                   AT END MOVE 'Y' TO WS-EOF
               END-READ
               IF WS-EOF = 'N'
                   UNSTRING SALES-REC DELIMITED BY ALL SPACE
                       INTO WS-REGION WS-ITEM WS-QTY-TEXT WS-PRICE-TEXT
                   END-UNSTRING
                   MOVE FUNCTION NUMVAL(WS-QTY-TEXT) TO WS-QTY
                   MOVE FUNCTION NUMVAL(WS-PRICE-TEXT) TO WS-PRICE
                   COMPUTE WS-AMOUNT ROUNDED = WS-QTY * WS-PRICE
                   IF WS-QTY >= 10
                       COMPUTE WS-AMOUNT ROUNDED = WS-AMOUNT * 0.95
                   END-IF
                   IF WS-FIRST = 'Y'
                       MOVE WS-REGION TO WS-CUR-REGION
                       MOVE 'N' TO WS-FIRST
                       DISPLAY 'REGION ' FUNCTION TRIM(WS-CUR-REGION)
                   ELSE
                       IF WS-REGION NOT = WS-CUR-REGION
                           MOVE WS-REG-TOTAL TO OUT-TOTAL
                           DISPLAY 'REGION TOTAL     ' OUT-TOTAL
                           MOVE ZERO TO WS-REG-TOTAL
                           MOVE WS-REGION TO WS-CUR-REGION
                           DISPLAY 'REGION '
                               FUNCTION TRIM(WS-CUR-REGION)
                       END-IF
                   END-IF
                   MOVE WS-QTY TO OUT-QTY
                   MOVE WS-AMOUNT TO OUT-AMOUNT
                   DISPLAY WS-ITEM OUT-QTY ' ' OUT-AMOUNT
                   ADD WS-AMOUNT TO WS-REG-TOTAL
                   ADD WS-AMOUNT TO WS-GRAND
               END-IF
           END-PERFORM
           CLOSE SALES-FILE
           MOVE WS-REG-TOTAL TO OUT-TOTAL
           DISPLAY 'REGION TOTAL     ' OUT-TOTAL
           MOVE WS-GRAND TO OUT-TOTAL
           DISPLAY 'GRAND TOTAL      ' OUT-TOTAL
           COMPUTE WS-TAX ROUNDED = WS-GRAND * 0.0825
           COMPUTE WS-TOTAL ROUNDED = WS-GRAND + WS-TAX
           MOVE WS-TAX TO OUT-TOTAL
           DISPLAY 'TAX              ' OUT-TOTAL
           MOVE WS-TOTAL TO OUT-TOTAL
           DISPLAY 'TOTAL            ' OUT-TOTAL
           STOP RUN.
