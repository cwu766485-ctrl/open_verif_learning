// Two P1 MESI controllers wired to their 32 KiB L1 arrays, plus the shared
// request arbiter. The Directory/L2 line engine connects through the exposed
// request, snoop, grant, and eight-beat data channels.
module DualL1MesiCluster #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input logic clock,
  input logic reset,

  input  logic cpu_req_valid [0:1],
  output logic cpu_req_ready [0:1],
  input  logic [31:0] cpu_req_addr [0:1],
  input  logic cpu_req_write [0:1],
  input  logic [7:0] cpu_req_wmask [0:1],
  input  logic [63:0] cpu_req_wdata [0:1],
  output logic cpu_resp_valid [0:1],
  input  logic cpu_resp_ready [0:1],
  output logic [31:0] cpu_resp_addr [0:1],
  output logic cpu_resp_write [0:1],
  output logic [63:0] cpu_resp_rdata [0:1],
  output logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1],
  output logic cpu_hit_event [0:1],
  output logic cpu_miss_event [0:1],
  // Stable verification tap: reports metadata writes only after the L1 array
  // accepts them, rather than exposing controller intent or private signals.
  output logic metadata_commit_valid [0:1],
  output logic [31:0] metadata_commit_line_addr [0:1],
  output coherence_protocol_pkg::mesi_state_t metadata_commit_state [0:1],
  output logic metadata_commit_is_snoop [0:1],

  output logic dir_req_valid,
  input  logic dir_req_ready_from_directory,
  output logic dir_req_src_id,
  output coherence_protocol_pkg::request_opcode_t dir_req_opcode,
  output logic [31:0] dir_req_line_addr,
  output logic [TXN_ID_WIDTH-1:0] dir_req_txn_id,

  // PutM data starts when the Directory grants the line-transfer slot.
  input  logic put_xfer_start [0:1],
  input  logic [31:0] put_xfer_addr [0:1],
  input  logic [TXN_ID_WIDTH-1:0] put_xfer_txn_id [0:1],
  output logic put_data_valid [0:1],
  input  logic put_data_ready [0:1],
  output logic [2:0] put_data_beat_idx [0:1],
  output logic [63:0] put_data [0:1],
  output logic put_data_last [0:1],

  input  logic grant_valid [0:1],
  output logic grant_ready [0:1],
  input  coherence_protocol_pkg::grant_opcode_t grant_opcode [0:1],
  input  logic [TXN_ID_WIDTH-1:0] grant_txn_id [0:1],
  input  logic grant_data_valid [0:1],
  output logic grant_data_ready [0:1],
  input  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id [0:1],
  input  logic [2:0] grant_data_beat_idx [0:1],
  input  logic [63:0] grant_data [0:1],
  input  logic grant_data_last [0:1],
  output logic grant_commit_valid [0:1],
  input  logic grant_commit_ready [0:1],
  output logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id [0:1],

  input  logic snoop_valid [0:1],
  output logic snoop_ready [0:1],
  input  logic [31:0] snoop_line_addr [0:1],
  input  coherence_protocol_pkg::snoop_opcode_t snoop_opcode [0:1],
  input  logic [TXN_ID_WIDTH-1:0] snoop_txn_id [0:1],
  output logic snoop_rsp_valid [0:1],
  input  logic snoop_rsp_ready [0:1],
  output coherence_protocol_pkg::snoop_response_t snoop_rsp_opcode [0:1],
  output logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id [0:1],
  output logic snoop_rsp_has_data [0:1],
  output logic snoop_data_valid [0:1],
  input  logic snoop_data_ready [0:1],
  output logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id [0:1],
  output logic [2:0] snoop_data_beat_idx [0:1],
  output logic [63:0] snoop_data [0:1],
  output logic snoop_data_last [0:1],

  output logic replace_valid [0:1],
  output logic [1:0] replace_way [0:1],
  output coherence_protocol_pkg::mesi_state_t replace_state [0:1],
  output logic [31:0] replace_line_addr [0:1],
  output logic [1:0] controller_protocol_error,
  output logic [1:0] array_protocol_error
);
  import coherence_protocol_pkg::*;

  request_opcode_t controller_req_opcode [0:1];
  logic [31:0] controller_req_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] controller_req_txn_id [0:1];
  logic [1:0] controller_req_valid;
  logic [1:0] controller_req_ready;
  logic [1:0] arb_req_valid;
  logic [1:0] arb_req_ready;
  request_opcode_t arb_req_opcode [0:1];
  logic [31:0] arb_req_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] arb_req_txn_id [0:1];

  typedef enum logic [3:0] {
    REPLACE_IDLE,
    REPLACE_CHECK,
    REPLACE_SEND_PUT,
    REPLACE_WAIT_XFER,
    REPLACE_READ_REQ,
    REPLACE_STREAM_M,
    REPLACE_WAIT_ACK,
    REPLACE_WAIT_COMMIT,
    REPLACE_INVALIDATE,
    REPLACE_REPLAY,
    REPLACE_ERROR
  } replace_state_t;

  for (genvar core = 0; core < 2; core = core + 1) begin : cores
    logic [31:0] lookup_addr;
    logic ctrl_cpu_req_valid;
    logic ctrl_cpu_req_ready;
    logic request_needs_replace;
    logic [31:0] ctrl_cpu_req_addr;
    logic ctrl_cpu_req_write;
    logic lookup_hit;
    logic [1:0] lookup_way;
    mesi_state_t lookup_state;
    logic [63:0] lookup_word;
    logic snoop_lookup_hit;
    mesi_state_t snoop_lookup_state;
    logic [1:0] allocation_way_q;
    logic [7:0] store_wmask_q;
    logic [63:0] store_wdata_q;

    logic ctrl_resp_valid;
    logic ctrl_resp_ready;
    logic [31:0] ctrl_resp_addr;
    logic ctrl_resp_write;
    logic [TXN_ID_WIDTH-1:0] ctrl_resp_txn_id;
    logic refill_valid;
    logic [2:0] refill_beat_idx;
    logic [63:0] refill_data;
    logic refill_last;
    logic snoop_meta_write_valid;
    logic snoop_meta_write_ready;
    logic [31:0] snoop_meta_write_line_addr;
    mesi_state_t snoop_meta_write_state;
    logic snoop_line_rd_valid;
    logic snoop_line_rd_ready;
    logic [31:0] snoop_line_rd_addr;
    logic array_line_data_valid;
    logic ctrl_snoop_array_data_ready;
    logic [2:0] array_line_data_beat_idx;
    logic [63:0] array_line_data;
    logic array_line_data_last;
    logic array_line_data_valid_int;
    logic [2:0] array_line_data_beat_idx_int;
    logic [63:0] array_line_data_int;
    logic array_line_data_last_int;
    logic array_line_data_ready;
    logic array_line_rd_valid;
    logic array_line_rd_ready;
    logic [31:0] array_line_rd_addr;
    logic array_line_rd_hit;
    logic snoop_line_rd_ready_int;
    logic evict_line_rd_valid;
    logic evict_line_rd_ready;
    logic array_rd_active_q;
    logic array_rd_owner_evict_q;
    logic array_rd_select_evict;
    logic ctrl_grant_valid;
    logic ctrl_grant_ready;
    logic [TXN_ID_WIDTH-1:0] ctrl_grant_txn_id;
    grant_opcode_t ctrl_grant_opcode;
    logic ctrl_grant_commit_valid;
    logic ctrl_grant_commit_ready;
    logic [TXN_ID_WIDTH-1:0] ctrl_grant_commit_txn_id;
    logic ctrl_cpu_meta_write_valid;
    logic ctrl_cpu_meta_write_ready;
    logic [31:0] ctrl_cpu_meta_write_line_addr;
    mesi_state_t ctrl_cpu_meta_write_state;
    logic array_cpu_meta_write_valid;
    logic array_cpu_meta_write_ready;
    logic [31:0] array_cpu_meta_write_line_addr;
    mesi_state_t array_cpu_meta_write_state;
    logic [1:0] replace_way_int;
    mesi_state_t replace_state_int;
    logic [31:0] replace_line_addr_int;
    replace_state_t replace_state_q;
    request_opcode_t replace_opcode_q;
    logic [31:0] replace_line_addr_q;
    logic [31:0] pending_cpu_addr_q;
    logic pending_cpu_write_q;
    logic [TXN_ID_WIDTH-1:0] replace_txn_q;
    logic [TXN_ID_WIDTH-1:0] replace_txn_counter_q;
    logic replace_protocol_error_q;
    logic arb_req_is_replace;
    logic evict_grant_ready;
    logic ctrl_protocol_error;
    logic array_refill_ready;
    logic array_store_ready;

    assign ctrl_cpu_req_addr =
      ((replace_state_q == REPLACE_CHECK) ||
       (replace_state_q == REPLACE_REPLAY)) ? pending_cpu_addr_q :
                                             cpu_req_addr[core];
    assign ctrl_cpu_req_write =
      ((replace_state_q == REPLACE_CHECK) ||
       (replace_state_q == REPLACE_REPLAY)) ? pending_cpu_write_q :
                                             cpu_req_write[core];
    assign lookup_addr = ctrl_resp_valid ? ctrl_resp_addr : ctrl_cpu_req_addr;
    assign request_needs_replace = !lookup_hit && replace_valid[core];
    // Keep controller valid driven only by registered replacement state.
    // A hit or cold miss with a free way skips CHECK but is replayed one cycle
    // later, shortening the path without forming a ready/valid loop.
    assign ctrl_cpu_req_valid = (replace_state_q == REPLACE_REPLAY);
    assign cpu_req_ready[core] = (replace_state_q == REPLACE_IDLE) &&
                                 ctrl_cpu_req_ready;
    // A read hit needs an existing MESI copy. A write hit is silent only in
    // E/M; an S-state store requires a Directory Upgrade and counts as a miss.
    assign cpu_hit_event[core] = !reset && cpu_req_valid[core] &&
      cpu_req_ready[core] && lookup_hit &&
      (!cpu_req_write[core] || (lookup_state == MESI_E) ||
       (lookup_state == MESI_M));
    assign cpu_miss_event[core] = !reset && cpu_req_valid[core] &&
      cpu_req_ready[core] && !cpu_hit_event[core];
    assign cpu_resp_valid[core] = ctrl_resp_valid &&
      (!ctrl_resp_write || array_store_ready);
    assign cpu_resp_addr[core] = ctrl_resp_addr;
    assign cpu_resp_write[core] = ctrl_resp_write;
    assign cpu_resp_txn_id[core] = ctrl_resp_txn_id;
    assign cpu_resp_rdata[core] = lookup_word;
    assign ctrl_resp_ready = cpu_resp_ready[core] && cpu_resp_valid[core];

    assign arb_req_is_replace = (replace_state_q == REPLACE_SEND_PUT);
    assign arb_req_valid[core] = arb_req_is_replace ? 1'b1 : controller_req_valid[core];
    assign arb_req_opcode[core] = arb_req_is_replace ? replace_opcode_q :
                                                       controller_req_opcode[core];
    assign arb_req_addr[core] = arb_req_is_replace ? replace_line_addr_q :
                                                    controller_req_addr[core];
    assign arb_req_txn_id[core] = arb_req_is_replace ? replace_txn_q :
                                                      controller_req_txn_id[core];
    assign controller_req_ready[core] = arb_req_ready[core] && !arb_req_is_replace;

    assign ctrl_grant_valid = grant_valid[core] &&
                              (replace_state_q != REPLACE_WAIT_ACK);
    assign ctrl_grant_opcode = grant_opcode[core];
    assign ctrl_grant_txn_id = grant_txn_id[core];
    assign ctrl_grant_commit_ready = grant_commit_ready[core] &&
                                     (replace_state_q != REPLACE_WAIT_COMMIT);
    assign evict_grant_ready = (grant_txn_id[core] == replace_txn_q) &&
                               (grant_opcode[core] == GRANT_PUT_ACK);
    assign grant_ready[core] = (replace_state_q == REPLACE_WAIT_ACK) ?
                               evict_grant_ready : ctrl_grant_ready;
    assign grant_commit_valid[core] =
      (replace_state_q == REPLACE_WAIT_COMMIT) || ctrl_grant_commit_valid;
    assign grant_commit_txn_id[core] =
      (replace_state_q == REPLACE_WAIT_COMMIT) ? replace_txn_q :
                                                 ctrl_grant_commit_txn_id;

    assign array_cpu_meta_write_valid =
      (replace_state_q == REPLACE_INVALIDATE) ? 1'b1 :
                                                ctrl_cpu_meta_write_valid;
    assign array_cpu_meta_write_line_addr =
      (replace_state_q == REPLACE_INVALIDATE) ? replace_line_addr_q :
                                                ctrl_cpu_meta_write_line_addr;
    assign array_cpu_meta_write_state =
      (replace_state_q == REPLACE_INVALIDATE) ? MESI_I :
                                                ctrl_cpu_meta_write_state;
    assign ctrl_cpu_meta_write_ready = array_cpu_meta_write_ready &&
                                       (replace_state_q != REPLACE_INVALIDATE);
    assign metadata_commit_is_snoop[core] =
      snoop_meta_write_valid && snoop_meta_write_ready;
    assign metadata_commit_valid[core] = metadata_commit_is_snoop[core] ||
      (array_cpu_meta_write_valid && array_cpu_meta_write_ready);
    assign metadata_commit_line_addr[core] = metadata_commit_is_snoop[core] ?
      snoop_meta_write_line_addr : array_cpu_meta_write_line_addr;
    assign metadata_commit_state[core] = metadata_commit_is_snoop[core] ?
      snoop_meta_write_state : array_cpu_meta_write_state;

    assign evict_line_rd_valid = (replace_state_q == REPLACE_READ_REQ);
    assign array_line_data_valid = array_rd_active_q && !array_rd_owner_evict_q &&
                                   array_line_data_valid_int;
    assign array_line_data_ready = array_rd_active_q &&
      (array_rd_owner_evict_q ? put_data_ready[core] :
                                ctrl_snoop_array_data_ready);
    assign put_data_valid[core] = array_rd_active_q && array_rd_owner_evict_q &&
                                  array_line_data_valid_int &&
                                  (replace_state_q == REPLACE_STREAM_M);
    assign put_data_beat_idx[core] = array_line_data_beat_idx_int;
    assign put_data[core] = array_line_data_int;
    assign put_data_last[core] = array_line_data_last_int;

    always_comb begin
      array_line_rd_valid = 1'b0;
      array_line_rd_addr = snoop_line_rd_addr;
      array_rd_select_evict = 1'b0;
      if (!array_rd_active_q) begin
        if (snoop_line_rd_valid) begin
          array_line_rd_valid = 1'b1;
          array_line_rd_addr = snoop_line_rd_addr;
        end else if (evict_line_rd_valid) begin
          array_line_rd_valid = 1'b1;
          array_line_rd_addr = replace_line_addr_q;
          array_rd_select_evict = 1'b1;
        end
      end
      snoop_line_rd_ready_int = array_line_rd_ready && !array_rd_active_q &&
                                snoop_line_rd_valid;
      evict_line_rd_ready = array_line_rd_ready && !array_rd_active_q &&
                            !snoop_line_rd_valid && evict_line_rd_valid;
    end

    always_ff @(posedge clock) begin
      if (reset) begin
        allocation_way_q <= '0;
        store_wmask_q <= '0;
        store_wdata_q <= '0;
        replace_state_q <= REPLACE_IDLE;
        replace_opcode_q <= REQ_PUTS;
        replace_line_addr_q <= '0;
        pending_cpu_addr_q <= '0;
        pending_cpu_write_q <= 1'b0;
        replace_txn_q <= '0;
        replace_txn_counter_q <= '0;
        replace_protocol_error_q <= 1'b0;
        array_rd_active_q <= 1'b0;
        array_rd_owner_evict_q <= 1'b0;
      end else if (cpu_req_valid[core] && cpu_req_ready[core]) begin
        pending_cpu_addr_q <= cpu_req_addr[core];
        pending_cpu_write_q <= cpu_req_write[core];
        store_wmask_q <= cpu_req_wmask[core];
        store_wdata_q <= cpu_req_wdata[core];
        if (request_needs_replace) begin
          replace_state_q <= REPLACE_CHECK;
        end else begin
          // A hit or a cold miss with a free way skips REPLACE_CHECK. Capture
          // the allocation way now; the registered REPLAY state submits the
          // request to the controller on the next cycle.
          allocation_way_q <= replace_way_int;
          replace_state_q <= REPLACE_REPLAY;
        end
      end else begin
        if (!array_rd_active_q && array_line_rd_valid && array_line_rd_ready) begin
          array_rd_active_q <= 1'b1;
          array_rd_owner_evict_q <= array_rd_select_evict;
        end else if (array_rd_active_q && array_line_data_valid_int &&
                     array_line_data_ready && array_line_data_last_int) begin
          array_rd_active_q <= 1'b0;
        end

        case (replace_state_q)
          REPLACE_CHECK: begin
            allocation_way_q <= replace_way_int;
            if (request_needs_replace) begin
              replace_line_addr_q <= replace_line_addr_int;
              replace_txn_q <= replace_txn_counter_q;
              replace_txn_counter_q <= replace_txn_counter_q + 1'b1;
              case (replace_state_int)
                MESI_S: begin replace_opcode_q <= REQ_PUTS; replace_state_q <= REPLACE_SEND_PUT; end
                MESI_E: begin replace_opcode_q <= REQ_PUTE; replace_state_q <= REPLACE_SEND_PUT; end
                MESI_M: begin replace_opcode_q <= REQ_PUTM; replace_state_q <= REPLACE_SEND_PUT; end
                default: begin
                  replace_protocol_error_q <= 1'b1;
                  replace_state_q <= REPLACE_ERROR;
                end
              endcase
            end else begin
              replace_state_q <= REPLACE_REPLAY;
            end
          end
          REPLACE_SEND_PUT: begin
            if (arb_req_valid[core] && arb_req_ready[core]) begin
              if (replace_opcode_q == REQ_PUTM)
                replace_state_q <= REPLACE_WAIT_XFER;
              else
                replace_state_q <= REPLACE_WAIT_ACK;
            end
          end
          REPLACE_WAIT_XFER: begin
            if (put_xfer_start[core] &&
                (put_xfer_addr[core] == replace_line_addr_q) &&
                (put_xfer_txn_id[core] == replace_txn_q))
              replace_state_q <= REPLACE_READ_REQ;
          end
          REPLACE_READ_REQ: begin
            if (evict_line_rd_valid && evict_line_rd_ready)
              replace_state_q <= REPLACE_STREAM_M;
          end
          REPLACE_STREAM_M: begin
            if (put_data_valid[core] && put_data_ready[core] &&
                put_data_last[core])
              replace_state_q <= REPLACE_WAIT_ACK;
          end
          REPLACE_WAIT_ACK: begin
            if (grant_valid[core] && grant_ready[core]) begin
              if (grant_opcode[core] == GRANT_PUT_ACK)
                replace_state_q <= REPLACE_WAIT_COMMIT;
              else begin
                replace_protocol_error_q <= 1'b1;
                replace_state_q <= REPLACE_ERROR;
              end
            end
          end
          REPLACE_WAIT_COMMIT: begin
            if (grant_commit_valid[core] && grant_commit_ready[core])
              replace_state_q <= REPLACE_INVALIDATE;
          end
          REPLACE_INVALIDATE: begin
            if (array_cpu_meta_write_valid && array_cpu_meta_write_ready)
              replace_state_q <= REPLACE_REPLAY;
          end
          REPLACE_REPLAY: begin
            if (ctrl_cpu_req_valid && ctrl_cpu_req_ready)
              replace_state_q <= REPLACE_IDLE;
          end
          default: begin end
        endcase
      end
    end

    MesiL1Controller #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) l1_controller (
      .clock(clock), .reset(reset),
      .cpu_req_valid(ctrl_cpu_req_valid), .cpu_req_ready(ctrl_cpu_req_ready),
      .cpu_req_addr(ctrl_cpu_req_addr), .cpu_req_write(ctrl_cpu_req_write),
      .cpu_req_hit(lookup_hit), .cpu_req_line_state(lookup_state),
      .cpu_resp_valid(ctrl_resp_valid), .cpu_resp_ready(ctrl_resp_ready),
      .cpu_resp_addr(ctrl_resp_addr), .cpu_resp_write(ctrl_resp_write),
      .cpu_resp_txn_id(ctrl_resp_txn_id),
      .dir_req_valid(controller_req_valid[core]),
      .dir_req_ready(controller_req_ready[core]),
      .dir_req_opcode(controller_req_opcode[core]),
      .dir_req_line_addr(controller_req_addr[core]),
      .dir_req_txn_id(controller_req_txn_id[core]),
      .grant_valid(ctrl_grant_valid), .grant_ready(ctrl_grant_ready),
      .grant_opcode(ctrl_grant_opcode), .grant_txn_id(ctrl_grant_txn_id),
      .grant_data_valid(grant_data_valid[core]),
      .grant_data_ready(grant_data_ready[core]),
      .grant_data_txn_id(grant_data_txn_id[core]),
      .grant_data_beat_idx(grant_data_beat_idx[core]),
      .grant_data(grant_data[core]), .grant_data_last(grant_data_last[core]),
      .refill_valid(refill_valid), .refill_ready(array_refill_ready),
      .refill_txn_id(), .refill_beat_idx(refill_beat_idx),
      .refill_data(refill_data), .refill_last(refill_last),
      .grant_commit_valid(ctrl_grant_commit_valid),
      .grant_commit_ready(ctrl_grant_commit_ready),
      .grant_commit_txn_id(ctrl_grant_commit_txn_id),
      .snoop_valid(snoop_valid[core]), .snoop_ready(snoop_ready[core]),
      .snoop_line_addr(snoop_line_addr[core]),
      .snoop_opcode(snoop_opcode[core]), .snoop_txn_id(snoop_txn_id[core]),
      .snoop_tag_hit(snoop_lookup_hit), .snoop_line_state(snoop_lookup_state),
      .snoop_rsp_valid(snoop_rsp_valid[core]),
      .snoop_rsp_ready(snoop_rsp_ready[core]),
      .snoop_rsp_opcode(snoop_rsp_opcode[core]),
      .snoop_rsp_txn_id(snoop_rsp_txn_id[core]),
      .snoop_rsp_has_data(snoop_rsp_has_data[core]),
      .snoop_line_rd_valid(snoop_line_rd_valid),
      .snoop_line_rd_ready(snoop_line_rd_ready),
      .snoop_line_rd_addr(snoop_line_rd_addr),
      .snoop_array_data_valid(array_line_data_valid),
      .snoop_array_data_ready(ctrl_snoop_array_data_ready),
      .snoop_array_beat_idx(array_line_data_beat_idx),
      .snoop_array_data(array_line_data), .snoop_array_last(array_line_data_last),
      .snoop_data_valid(snoop_data_valid[core]),
      .snoop_data_ready(snoop_data_ready[core]),
      .snoop_data_txn_id(snoop_data_txn_id[core]),
      .snoop_data_beat_idx(snoop_data_beat_idx[core]),
      .snoop_data(snoop_data[core]), .snoop_data_last(snoop_data_last[core]),
      .cpu_meta_write_valid(ctrl_cpu_meta_write_valid),
      .cpu_meta_write_ready(ctrl_cpu_meta_write_ready),
      .cpu_meta_write_line_addr(ctrl_cpu_meta_write_line_addr),
      .cpu_meta_write_state(ctrl_cpu_meta_write_state),
      .snoop_meta_write_valid(snoop_meta_write_valid),
      .snoop_meta_write_ready(snoop_meta_write_ready),
      .snoop_meta_write_line_addr(snoop_meta_write_line_addr),
      .snoop_meta_write_state(snoop_meta_write_state),
      .protocol_error(ctrl_protocol_error)
    );

    MesiL1Array #(.SETS(128), .WAYS(4), .TAG_WIDTH(19)) l1_array (
      .clock(clock), .reset(reset),
      .cpu_lookup_addr(lookup_addr), .cpu_lookup_hit(lookup_hit),
      .cpu_lookup_way(lookup_way), .cpu_lookup_state(lookup_state),
      .cpu_lookup_word(lookup_word),
      .snoop_lookup_addr(snoop_line_addr[core]),
      .snoop_lookup_hit(snoop_lookup_hit),
      .snoop_lookup_way(),
      .snoop_lookup_state(snoop_lookup_state),
      .replace_valid(replace_valid[core]), .replace_way(replace_way_int),
      .replace_state(replace_state_int),
      .replace_line_addr(replace_line_addr_int),
      .cpu_meta_write_valid(array_cpu_meta_write_valid),
      .cpu_meta_write_ready(array_cpu_meta_write_ready),
      .cpu_meta_write_line_addr(array_cpu_meta_write_line_addr),
      .cpu_meta_write_state(array_cpu_meta_write_state),
      .snoop_meta_write_valid(snoop_meta_write_valid),
      .snoop_meta_write_ready(snoop_meta_write_ready),
      .snoop_meta_write_line_addr(snoop_meta_write_line_addr),
      .snoop_meta_write_state(snoop_meta_write_state),
      .refill_valid(refill_valid), .refill_ready(array_refill_ready),
      .refill_line_addr(ctrl_resp_addr), .refill_way(allocation_way_q),
      .refill_beat_idx(refill_beat_idx), .refill_data(refill_data),
      .refill_last(refill_last),
      .cpu_store_valid(cpu_resp_valid[core] && ctrl_resp_write &&
                       cpu_resp_ready[core]),
      .cpu_store_ready(array_store_ready), .cpu_store_addr(ctrl_resp_addr),
      .cpu_store_way(lookup_way), .cpu_store_wmask(store_wmask_q),
      .cpu_store_wdata(store_wdata_q),
      .line_rd_valid(array_line_rd_valid),
      .line_rd_ready(array_line_rd_ready), .line_rd_addr(array_line_rd_addr),
      .line_rd_hit(array_line_rd_hit), .line_data_valid(array_line_data_valid_int),
      .line_data_ready(array_line_data_ready),
      .line_data_beat_idx(array_line_data_beat_idx_int),
      .line_data(array_line_data_int), .line_data_last(array_line_data_last_int),
      .protocol_error(array_protocol_error[core])
    );

    assign replace_way[core] = replace_way_int;
    assign replace_state[core] = replace_state_int;
    assign replace_line_addr[core] = replace_line_addr_int;
    assign snoop_line_rd_ready = snoop_line_rd_ready_int;
    assign array_line_data_beat_idx = array_line_data_beat_idx_int;
    assign array_line_data = array_line_data_int;
    assign array_line_data_last = array_line_data_last_int;
    assign controller_protocol_error[core] =
      ctrl_protocol_error | replace_protocol_error_q |
      ((array_line_rd_valid && array_line_rd_ready) && !array_line_rd_hit);
  end

  CoherenceRequestArbiter #(.TXN_ID_WIDTH(TXN_ID_WIDTH)) request_arbiter (
    .clock(clock), .reset(reset),
    .in_valid(arb_req_valid), .in_ready(arb_req_ready),
    .in_opcode(arb_req_opcode), .in_line_addr(arb_req_addr),
    .in_txn_id(arb_req_txn_id), .out_valid(dir_req_valid),
    .out_ready(dir_req_ready_from_directory), .out_src_id(dir_req_src_id),
    .out_opcode(dir_req_opcode), .out_line_addr(dir_req_line_addr),
    .out_txn_id(dir_req_txn_id)
  );

endmodule
