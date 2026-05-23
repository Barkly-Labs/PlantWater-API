#pragma once

/**
 * 💓 Heartbeat Module
 * Sends periodic heartbeat checks to backend server
 * Non-blocking implementation (can be upgraded to FreeRTOS task)
 */

/**
 * Initialize heartbeat subsystem
 */
void heartbeat_init();

/**
 * Heartbeat tick - called from main loop
 * Sends heartbeat at configured interval
 * Non-blocking - returns immediately if not time yet
 */
void heartbeat_tick();

/**
 * Get last heartbeat time
 * Returns: milliseconds since last heartbeat was sent
 */
uint32_t heartbeat_get_last_ms();

/**
 * Debug: Print heartbeat status
 */
void heartbeat_debug_print();

#endif // HEARTBEAT_H
