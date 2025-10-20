#include QMK_KEYBOARD_H
#include "keymap_german.h"

// Custom keycodes for literal [ and ] with home-row mod hold
enum custom_keycodes {
    LBRC_MOD = SAFE_RANGE,
    RBRC_MOD
};

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    static uint16_t timer_lbrc;
    static uint16_t timer_rbrc;

    switch (keycode) {
        case LBRC_MOD:
            if (record->event.pressed) {
                timer_lbrc = timer_read();
            } else {
                if (timer_elapsed(timer_lbrc) < TAPPING_TERM) {
                    // Tap -> literal [ via AltGr + 8
                    register_code(KC_RALT);
                    tap_code(KC_8);
                    unregister_code(KC_RALT);
                } else {
                    // Hold -> Left Alt
                    register_code(KC_LALT);
                    unregister_code(KC_LALT);
                }
            }
            return false; // Handled

        case RBRC_MOD:
            if (record->event.pressed) {
                timer_rbrc = timer_read();
            } else {
                if (timer_elapsed(timer_rbrc) < TAPPING_TERM) {
                    // Tap -> literal ] via AltGr + 9
                    register_code(KC_RALT);
                    tap_code(KC_9);
                    unregister_code(KC_RALT);
                } else {
                    // Hold -> GUI
                    register_code(KC_LGUI);
                    unregister_code(KC_LGUI);
                }
            }
            return false; // Handled
    }
    return true;
}

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {

    /* Layer 0: Base */
    [0] = LAYOUT_split_3x5_3(
        KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,             KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,
        LSFT_T(KC_A), LCTL_T(KC_S), LALT_T(KC_D), LGUI_T(KC_F), KC_G,    KC_H, RGUI_T(KC_J), LALT_T(KC_K), RCTL_T(KC_L), RSFT_T(KC_SCLN),
        KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,             KC_N,    KC_M,    KC_COMMA, KC_DOT,  KC_SLASH,
        LT(3, KC_DELETE), LT(2, KC_TAB), LT(1, KC_ESCAPE),   LT(1, KC_ENTER), LT(2, KC_SPACE), LT(3, KC_BSPC)
    ),

    /* Layer 1: Symbols / German special keys */
    [1] = LAYOUT_split_3x5_3(
        KC_GRAVE,  RALT(KC_MINUS), LSFT(KC_8),  LSFT(KC_9),  KC_EQUAL,           RALT(KC_E), KC_7,    KC_8,    KC_9,    KC_LBRC,
        LSFT_T(KC_NUBS), LCTL_T(KC_KP_SLASH), LBRC_MOD, RBRC_MOD, KC_NONUS_HASH, RALT(KC_Q), RGUI_T(KC_4), RALT_T(KC_5), RCTL_T(KC_6), RSFT_T(KC_QUOTE),
        RALT(KC_NUBS), RALT(KC_RBRC), RALT(KC_7),  RALT(KC_0),  KC_RBRC,          KC_0,    KC_1,    KC_2,    KC_3,    KC_MINUS,
        KC_TRNS, KC_TRNS, KC_TRNS,                                KC_TRNS, KC_TRNS, KC_TRNS
    ),

    /* Layer 2: Media / Navigation */
    [2] = LAYOUT_split_3x5_3(
        KC_ESCAPE,  KC_VOLD, KC_MUTE, KC_VOLU, KC_SCRL,          KC_PSCR, KC_PGDN, KC_UP,   KC_PGUP, KC_PAUSE,
        LSFT_T(KC_TAB), LCTL_T(KC_MPLY), LALT_T(KC_MSTP), LGUI_T(KC_MNXT), KC_NO,   KC_HOME, RGUI_T(KC_LEFT), RALT_T(KC_DOWN), RCTL_T(KC_RIGHT), RSFT_T(KC_END),
        KC_NO, LCTL(KC_KP_MINUS), LCTL(KC_KP_0), LCTL(KC_KP_PLUS), KC_NO,            KC_INSERT,  RALT(KC_M),  RALT(KC_2),  RALT(KC_3),  KC_APPLICATION,
        KC_TRNS, KC_TRNS, KC_TRNS,                                KC_TRNS, KC_TRNS, KC_TRNS
    ),

    /* Layer 3: RGB / Function */
    [3] = LAYOUT_split_3x5_3(
        KC_NO,   QK_RGB_MATRIX_TOGGLE,   QK_RGB_MATRIX_MODE_NEXT,   QK_UNDERGLOW_TOGGLE,   QK_UNDERGLOW_MODE_NEXT,              KC_F1,   KC_F2,   KC_F3,   KC_F4,   KC_F5,
        KC_NO, LCTL_T(KC_NO), LALT_T(KC_NO), LGUI_T(KC_NO), KC_NO,   KC_F6, RGUI_T(KC_F7), RALT_T(KC_F8), RCTL_T(KC_F9), KC_F10,
        QK_CLEAR_EEPROM,   QK_BOOT,   KC_NO,   KC_NO,   KC_NO,              KC_NO,   KC_NO,   KC_NO,   KC_F11,  KC_F12,
        KC_TRNS, KC_TRNS, KC_TRNS,                                KC_TRNS, KC_TRNS, KC_TRNS
    )
};
