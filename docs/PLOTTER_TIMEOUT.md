# Plotter Timeout and Unexpected Stops

This document describes the analysis of plotting stops unexpectedly, the root cause, and the fixes implemented.

## Problem Description

Plotting would stop with no clear cause. A workaround was to:

1. Select the pause button on the plotter control panel (sends M0 to the printer)
2. Hit the physical button on the printer to continue

This workaround caused plots to take longer and introduced other problems.

## Root Cause: Timeout Deadlock in PlotterCore

The backend uses `PlotterCore` to stream G-code to the plotter. It waits for an `ok` response from the printer before sending the next command (flow control). When the printer does not send `ok` within 5 seconds:

1. A warning was logged: `Timeout waiting for 'ok' after command: ...`
2. `self.clear` remained `False`
3. The send loop in `_sendnext()` waited indefinitely on `while not self.clear`
4. No further G-code was sent, so plotting stopped

The only way to recover was to pause (which set `printing=False` and exited the wait loop). That matched the observed workaround behavior.

## Why the Printer Might Stop Sending `ok`

Common causes:

- **Raspberry Pi USB serial issues**: Buffer overflows, USB interrupt latency, and brief communication blackouts are known on Pi hardware.
- **Docker + USB**: Serial passthrough adds a layer; USB hiccups can cause problems.
- **Printer busy**: Printer is still executing and has not yet sent `ok`.
- **Serial noise or cable**: Intermittent connection or interference.

## Fixes Implemented

### 1. Timeout Deadlock Recovery

In `backend/app/plotter_core.py`, when a timeout occurs waiting for `ok`, we now set `self.clear = True` so the send loop can continue instead of hanging indefinitely. Plotting should auto-recover after a timeout.

### 2. M108 on Resume

Marlin’s M0 command pauses and waits for user input. To resume programmatically, we send **M108** when the user hits resume in the UI. This unpauses the printer without requiring the physical button.

## Additional Recommendations

### Raspberry Pi USB Tuning

If `Timeout waiting for 'ok'` appears frequently in logs:

- **Lower baud rate**: If using 115200, try 57600 or 38400.
- **Boot config** (`/boot/config.txt`):
  - `dwc_otg.fiq_fix_enable=2` (if supported)
  - `arm_freq_min=1000` to reduce CPU throttling
- **USB power**: Use a powered USB hub if the plotter draws significant current.

### Run Natively on Pi

Running outside Docker (see [RUNNING_NATIVE_ON_RASPBERRY_PI.md](RUNNING_NATIVE_ON_RASPBERRY_PI.md)) can reduce USB serial overhead and avoid Docker passthrough issues.

### Browser Sleep

When the user’s computer sleeps, the browser tab is throttled and the UI may stop updating. The backend runs on the Pi and continues plotting; the UI is display-only. Consider using the Page Visibility API to show a message when the tab is hidden: “Plotting may still be running. Check the plotter.”

## Marlin Commands Reference

- **M0 / M1**: Pause and wait for user (displays "paused for user")
- **M108**: Resume from M0/M1 pause (programmatic unpause)

## Logging and Diagnostics

Enable `LOG_LEVEL=DEBUG` and watch for:

- `Timeout waiting for 'ok' after command: ...` — indicates the deadlock condition (now auto-recovered)
