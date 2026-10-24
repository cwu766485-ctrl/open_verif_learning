package coherence_protocol_pkg;
  parameter int ADDR_WIDTH = 32;
  localparam int LINE_BYTES = 64;
  localparam int WORD_BYTES = 8;
  localparam int LINE_BEATS = 8;
  localparam int BEAT_WIDTH = 64;
  parameter int TXN_ID_WIDTH = 4;

  typedef enum logic [1:0] {
    MESI_I = 2'b00,
    MESI_S = 2'b01,
    MESI_E = 2'b10,
    MESI_M = 2'b11
  } mesi_state_t;

  typedef enum logic [1:0] {
    DIR_I = 2'b00,
    DIR_S = 2'b01,
    DIR_U = 2'b10
  } directory_state_t;

  typedef enum logic [2:0] {
    REQ_GETS    = 3'b000,
    REQ_GETM    = 3'b001,
    REQ_UPGRADE = 3'b010,
    REQ_PUTS    = 3'b011,
    REQ_PUTE    = 3'b100,
    REQ_PUTM    = 3'b101
  } request_opcode_t;

  typedef enum logic {
    SNOOP_READ       = 1'b0,
    SNOOP_INVALIDATE = 1'b1
  } snoop_opcode_t;

  typedef enum logic [1:0] {
    SNOOP_RSP_ACK     = 2'b00,
    SNOOP_RSP_INV_ACK = 2'b01,
    SNOOP_RSP_DATA    = 2'b10
  } snoop_response_t;

  typedef enum logic [2:0] {
    GRANT_DATA_S = 3'b000,
    GRANT_DATA_E = 3'b001,
    GRANT_DATA_M = 3'b010,
    GRANT_M      = 3'b011,
    GRANT_PUT_ACK= 3'b100
  } grant_opcode_t;

  typedef enum logic [1:0] {
    XFER_L2_REFILL = 2'b00,
    XFER_PUTM_TO_L2 = 2'b01
  } line_xfer_kind_t;

  function automatic logic [ADDR_WIDTH-1:0] line_align(
    input logic [ADDR_WIDTH-1:0] addr
  );
    line_align = {addr[ADDR_WIDTH-1:6], 6'b0};
  endfunction

  function automatic logic [1:0] core_bit(input logic core_id);
    core_bit = core_id ? 2'b10 : 2'b01;
  endfunction

  function automatic mesi_state_t grant_to_mesi(input grant_opcode_t opcode);
    case (opcode)
      GRANT_DATA_S: grant_to_mesi = MESI_S;
      GRANT_DATA_E: grant_to_mesi = MESI_E;
      GRANT_DATA_M,
      GRANT_M:      grant_to_mesi = MESI_M;
      default:      grant_to_mesi = MESI_I;
    endcase
  endfunction

  function automatic logic grant_contains_data(input grant_opcode_t opcode);
    grant_contains_data = (opcode == GRANT_DATA_S) ||
                          (opcode == GRANT_DATA_E) ||
                          (opcode == GRANT_DATA_M);
  endfunction
endpackage
