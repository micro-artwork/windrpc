/* =========================================================================
 * USER-WRITTEN FILE: Business Logic Callbacks
 * =========================================================================
 * Implement application logic in callback functions defined by WindRPC spec.
 * Returns 0 on success.
 */
#include <stdio.h>
#include "windrpc.h"

// Callback 1: Power Manager -> Get Power Status (RPC ID: 0x0801)
int32_t windrpc_on_get_power_status(
    const void *req,
    rpc_power_manager_PowerStatus_t *res,
    void *context)
{
    (void)req;
    (void)context;

    printf("  [C-SERVER-CALLBACK] Called windrpc_on_get_power_status()\n");
    res->voltage_mv = 3300;   // 3.3V
    res->current_ma = 450;    // 450mA
    res->is_charging = true;  // Charging
    return 0; // Return 0 for SUCCESS
}

// Callback 2: Power Manager -> Subscribe Charging Alert Notification (RPC ID: 0x0802)
int32_t windrpc_on_subscribe_charging_alert(
    const rpc_types_Subscribe_t *req,
    rpc_types_Status_t *res,
    void *context)
{
    (void)req;
    (void)context;

    printf("  [C-SERVER-CALLBACK] Called windrpc_on_subscribe_charging_alert()\n");
    res->code = 0; // Success
    return 0;
}

// Callback 3: Device Control -> Set LED Color (RPC ID: 0x0901)
int32_t windrpc_on_set_led_color(
    const rpc_device_control_LedColor_t *req,
    rpc_device_control_LedResult_t *res,
    void *context)
{
    (void)context;

    printf("  [C-SERVER-CALLBACK] Called windrpc_on_set_led_color(): RGB(%u, %u, %u)\n",
           (unsigned int)req->r, (unsigned int)req->g, (unsigned int)req->b);

    res->success = true;
    return 0; // Return 0 for SUCCESS
}
