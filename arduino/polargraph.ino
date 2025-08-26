// polargraph.ino
// Example firmware skeleton for Arduino

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd == "START") {
      Serial.println("Drawing started");
    } else if (cmd == "STOP") {
      Serial.println("Drawing stopped");
    } else if (cmd == "PAUSE") {
      Serial.println("Drawing paused");
    } else {
      Serial.println("Unknown command");
    }
  }
}
