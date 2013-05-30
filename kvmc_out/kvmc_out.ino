/* kvmc_out
 * Copyright (c) 2012 George Murdocca
 * http://murdocca.com.au
 *
 * kvmc_out is free software: you can redistribute it and/or modify
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

// Message Types
#define KEYBOARD 0
#define KEYBOARD_MODKEY 1
#define MOUSE_BUTTON 2
#define MOUSE_MOVE 3
#define MOUSE_WHEEL 4
#define SERIAL_DATA 5
#define REINIT 6
#define SC 7

// Digital Pin Assignments
#define LED_PIN 11
#define SC_UP 12
#define SC_DOWN 13
#define SC_LEFT 14
#define SC_RIGHT 15
#define SC_MENU 16
#define SC_ZOOM 17

HardwareSerial Uart = HardwareSerial();
int byte_counter = 0;
char incoming_byte;
char* packet;
boolean sc_menu_state = false;
boolean menu_button_pressed_last = false;

void toggle_sc_menu_state(){
    if (sc_menu_state)
      sc_menu_state = false;
    else
      sc_menu_state = true;
}

void hide_sc_menu(){
  if (menu_button_pressed_last){
    toggle_sc_menu_state();
    menu_button_pressed_last = false;
  }
  if (sc_menu_state){
    digitalWrite(SC_MENU, LOW);
    delay(50);
    toggle_sc_menu_state();
  }
}

void reinit(){
  Keyboard.set_key1(0);
  Keyboard.set_key2(0);
  Keyboard.set_key3(0);
  Keyboard.set_key4(0);
  Keyboard.set_key5(0);
  Keyboard.set_key6(0);
  Keyboard.set_modifier(0);
  Keyboard.send_now();
  Mouse.set_buttons(0, 0, 0);
  Mouse.move(0, 0);
  hide_sc_menu();
}

int get_msg_type(char msg_byte){
  //return(msg_byte >> 5);
  return(msg_byte & 7);
}

int get_msg_payload(char msg_byte){
  // returns first 5 bits of byte
  return(msg_byte >> 3);
}

void setup(){
    Uart.begin(115200);
    Serial.begin(9600);
    pinMode(LED_PIN, OUTPUT);
    pinMode(SC_UP, OUTPUT);
    pinMode(SC_DOWN, OUTPUT);
    pinMode(SC_LEFT, OUTPUT);
    pinMode(SC_RIGHT, OUTPUT);
    pinMode(SC_MENU, OUTPUT);
    pinMode(SC_ZOOM, OUTPUT);
}

void loop(){
  digitalWrite(LED_PIN, LOW);
  digitalWrite(SC_UP, HIGH);
  digitalWrite(SC_DOWN, HIGH);
  digitalWrite(SC_LEFT, HIGH);
  digitalWrite(SC_RIGHT, HIGH);
  digitalWrite(SC_MENU, HIGH);
  digitalWrite(SC_ZOOM, HIGH);
  if (Serial.available()){
    Uart.print(Serial.read(), BYTE);
  }
  if (Uart.available()) {
    digitalWrite(LED_PIN, HIGH);
    incoming_byte = Uart.read();
    int msg_type = get_msg_type(incoming_byte);
    int msg_payload = get_msg_payload(incoming_byte);
    if (msg_type == KEYBOARD){
      while(true){
        if (Uart.available()){
          packet[byte_counter] = Uart.read();
          byte_counter++;
          if (byte_counter == 6){
            byte_counter = 0;
            Keyboard.set_key1(packet[0]);
            Keyboard.set_key2(packet[1]);
            Keyboard.set_key3(packet[2]);
            Keyboard.set_key4(packet[3]);
            Keyboard.set_key5(packet[4]);
            Keyboard.set_key6(packet[5]);
            Keyboard.send_now();
            packet = "";
            break;
          }
        }
      }
      hide_sc_menu();
    }
    else if (msg_type == KEYBOARD_MODKEY){
      Keyboard.set_modifier(msg_payload);
      Keyboard.send_now();
      hide_sc_menu();
    }
    else if (msg_type == MOUSE_BUTTON){
      Mouse.set_buttons((msg_payload & 0x01) != 0,
                        (msg_payload & 0x02) != 0,
                        (msg_payload & 0x04) != 0);      
      hide_sc_menu();
    }
    else if (msg_type == MOUSE_MOVE){
      while(true){
        if (Uart.available()){
          packet[byte_counter] = Uart.read();
          byte_counter++;
          if (byte_counter == 2){
            byte_counter = 0;
            Mouse.move(packet[0], packet[1]);
            packet = "";
            break;
          }
        }
      }
      hide_sc_menu();
    }
    else if (msg_type == MOUSE_WHEEL){
      if (msg_payload == 0){
        Mouse.scroll(1);
      }
      else{
        Mouse.scroll(-1);
      }
      hide_sc_menu();
    }
    else if (msg_type == SERIAL_DATA){
      while(!Uart.available());
      Serial.print(Uart.read(), BYTE);
    }
    else if (msg_type == REINIT){
      reinit();
    }
    else if (msg_type == SC){
      menu_button_pressed_last = false;
      while(!Uart.available());
      incoming_byte = Uart.read();
      if (incoming_byte &  1)
        digitalWrite(SC_UP, LOW);
      if (incoming_byte &  2)
        digitalWrite(SC_DOWN, LOW);
      if (incoming_byte &  4)
        digitalWrite(SC_LEFT, LOW);
      if (incoming_byte &  8)
        digitalWrite(SC_RIGHT, LOW);
      if (incoming_byte &  16){
        digitalWrite(SC_MENU, LOW);
        toggle_sc_menu_state();
        menu_button_pressed_last = true;
      }
      if (incoming_byte &  32)
        digitalWrite(SC_ZOOM, LOW);
      delay(50);
    }
  }
}

