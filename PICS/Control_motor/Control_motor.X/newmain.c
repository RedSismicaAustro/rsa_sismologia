#include <xc.h>
#include <stdint.h>
#include <stdbool.h>

// Frecuencia del oscilador interno
#define _XTAL_FREQ 4000000UL

// CONFIG PIC16F628A
#pragma config FOSC = INTOSCIO
#pragma config WDTE = OFF
#pragma config PWRTE = ON
#pragma config MCLRE = ON
#pragma config BOREN = ON
#pragma config LVP = OFF
#pragma config CPD = OFF
#pragma config CP = OFF

#define BUFFER_SIZE 20

// Variables de prueba
int16_t pos_m1 = 0;
int16_t pos_m2 = 0;

char rx_buffer[BUFFER_SIZE];
uint8_t rx_index = 0;

// Prototipos
void inicializar_pic(void);
void inicializar_usart(void);

bool uart_disponible(void);
char uart_rx_char(void);
void uart_tx_char(char c);
void uart_tx_texto(const char *txt);
void uart_tx_numero(int16_t valor);

void procesar_caracter(char c);
void procesar_comando(char *cmd);
bool texto_igual(const char *a, const char *b);

void main(void)
{
    inicializar_pic();
    inicializar_usart();

    uart_tx_texto("\r\nOK PIC16F628A READY\r\n");

    while (1)
    {
        if (uart_disponible())
        {
            char c = uart_rx_char();
            procesar_caracter(c);
        }
    }
}

void inicializar_pic(void)
{
    // Comparadores apagados por ahora.
    // Esta prueba es solo de USART.
    CMCON = 0x07;

    // PORTA como entradas por ahora
    TRISA = 0b11111111;

    /*
     * PORTB:
     * RB0 = libre por ahora / futura INT
     * RB1 = RX entrada
     * RB2 = TX salida
     * RB3 = salida futura M2_EN
     * RB4 = salida futura M1_EN
     * RB5 = libre
     * RB6/RB7 = programación
     */
    TRISB = 0b11100011;

    PORTA = 0x00;
    PORTB = 0x00;
}

void inicializar_usart(void)
{
    /*
     * USART asincrónico
     * Fosc = 4 MHz
     * Baudrate = 9600
     * BRGH = 1
     * SPBRG = 25
     */
    TXSTA = 0b00100100;   // TXEN=1, BRGH=1
    RCSTA = 0b10010000;   // SPEN=1, CREN=1
    SPBRG = 25;
}

bool uart_disponible(void)
{
    return PIR1bits.RCIF ? true : false;
}

char uart_rx_char(void)
{
    if (RCSTAbits.OERR)
    {
        RCSTAbits.CREN = 0;
        RCSTAbits.CREN = 1;
    }

    return RCREG;
}

void uart_tx_char(char c)
{
    while (!PIR1bits.TXIF);
    TXREG = c;
}

void uart_tx_texto(const char *txt)
{
    while (*txt)
    {
        uart_tx_char(*txt);
        txt++;
    }
}

void uart_tx_numero(int16_t valor)
{
    char txt[8];
    uint8_t i = 0;
    uint8_t j;
    bool negativo = false;

    if (valor == 0)
    {
        uart_tx_char('0');
        return;
    }

    if (valor < 0)
    {
        negativo = true;
        valor = -valor;
    }

    while (valor > 0 && i < sizeof(txt))
    {
        txt[i++] = '0' + (valor % 10);
        valor = valor / 10;
    }

    if (negativo)
    {
        uart_tx_char('-');
    }

    for (j = i; j > 0; j--)
    {
        uart_tx_char(txt[j - 1]);
    }
}

void procesar_caracter(char c)
{
    // Enter recibido: procesar comando
    if (c == '\r' || c == '\n')
    {
        if (rx_index > 0)
        {
            rx_buffer[rx_index] = '\0';
            procesar_comando(rx_buffer);
            rx_index = 0;
        }
        return;
    }

    // Evitar desbordamiento
    if (rx_index < BUFFER_SIZE - 1)
    {
        rx_buffer[rx_index++] = c;
    }
    else
    {
        rx_index = 0;
        uart_tx_texto("ERR BUFFER\r\n");
    }
}

void procesar_comando(char *cmd)
{
    if (texto_igual(cmd, "PING"))
    {
        uart_tx_texto("OK PONG\r\n");
    }
    else if (texto_igual(cmd, "S"))
    {
        uart_tx_texto("OK STATE IDLE\r\n");
    }
    else if (texto_igual(cmd, "A1"))
    {
        pos_m1++;
        uart_tx_texto("OK M1 STEP + POS=");
        uart_tx_numero(pos_m1);
        uart_tx_texto("\r\n");
    }
    else if (texto_igual(cmd, "R1"))
    {
        pos_m1--;
        uart_tx_texto("OK M1 STEP - POS=");
        uart_tx_numero(pos_m1);
        uart_tx_texto("\r\n");
    }
    else if (texto_igual(cmd, "A2"))
    {
        pos_m2++;
        uart_tx_texto("OK M2 STEP + POS=");
        uart_tx_numero(pos_m2);
        uart_tx_texto("\r\n");
    }
    else if (texto_igual(cmd, "R2"))
    {
        pos_m2--;
        uart_tx_texto("OK M2 STEP - POS=");
        uart_tx_numero(pos_m2);
        uart_tx_texto("\r\n");
    }
    else if (texto_igual(cmd, "P"))
    {
        uart_tx_texto("OK POS M1=");
        uart_tx_numero(pos_m1);
        uart_tx_texto(" M2=");
        uart_tx_numero(pos_m2);
        uart_tx_texto("\r\n");
    }
    else if (texto_igual(cmd, "X"))
    {
        uart_tx_texto("OK STOP\r\n");
    }
    else
    {
        uart_tx_texto("ERR CMD\r\n");
    }
}

bool texto_igual(const char *a, const char *b)
{
    while (*a && *b)
    {
        if (*a != *b)
        {
            return false;
        }

        a++;
        b++;
    }

    return (*a == '\0' && *b == '\0');
}