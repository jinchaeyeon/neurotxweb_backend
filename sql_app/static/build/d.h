static void ble_stack_init(void)

{

    ret_code_t err_code;

    err_code = nrf_sdh_enable_request();

    APP_ERROR_CHECK(err_code);

    // Configure the BLE stack using the default settings.

    // Fetch the start address of the application RAM.

    uint32_t ram_start = 0;

    err_code = nrf_sdh_ble_default_cfg_set(APP_BLE_CONN_CFG_TAG, &ram_start);

    APP_ERROR_CHECK(err_code);

    // Enable BLE stack.

    err_code = nrf_sdh_ble_enable(&ram_start);

    APP_ERROR_CHECK(err_code);

    // Register a handler for BLE events.

    NRF_SDH_BLE_OBSERVER(m_ble_observer, APP_BLE_OBSERVER_PRIO, ble_evt_handler, NULL);
}