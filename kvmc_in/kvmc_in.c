/* kvmc_in
 * Copyright (c) 2018 LinuxDojo
 * http//linuxdojo.com
 *
 * kvmc_in is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published
 * by the Free Software Foundation, either version 3 of the License,
 * or (at your option) any later version.
 *
 * kvmc_in is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You can obtain a copy of the GNU General Public License along at:
 * http://www.gnu.org/licenses/.
 */

#include <avr/io.h>
#include <avr/pgmspace.h>
#include <stdint.h>
#include <util/delay.h>
#include "usb_serial.h"
#include "uart.h"

#define LED_CONFIG  (DDRD |= (1<<6))
#define LED_ON      (PORTD |= (1<<6))
#define LED_OFF     (PORTD &= ~(1<<6))
#define CPU_PRESCALE(n) (CLKPR = 0x80, CLKPR = (n))

int main(void){

    int bytes_available;
    int n;

    CPU_PRESCALE(0);
    LED_CONFIG;
    usb_init();
    uart_init(115200);
    while (1){
        LED_OFF;
        while (!usb_configured());
        _delay_ms(1000);
        usb_serial_flush_input();
        LED_ON;
        while (usb_serial_get_control() & USB_SERIAL_DTR){
            bytes_available = usb_serial_available();
            for (int i = 0; i < bytes_available; i++){
                n = usb_serial_getchar();
                if (n >= 0) uart_putchar(n);
            }
            bytes_available = uart_available();
            for (int i = 0; i < bytes_available; i++){
                n = uart_getchar();
                if (n >= 0) usb_serial_putchar(n);
            }
        }
    }
}

