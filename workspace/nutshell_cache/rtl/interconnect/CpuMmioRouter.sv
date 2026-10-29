// Routes cacheable requests through the dual-L1 cluster and serializes the
// uncached MMIO bypass. The single-outstanding MMIO contract is unchanged.
module CpuMmioRouter #(
  parameter int TXN_ID_WIDTH = coherence_protocol_pkg::TXN_ID_WIDTH
) (
  input logic clock,
  input logic reset,
  input logic fatal_error,
  input logic cpu_req_valid [0:1],
  output logic cpu_req_ready [0:1],
  input logic [31:0] cpu_req_addr [0:1],
  input logic cpu_req_write [0:1],
  input logic [7:0] cpu_req_wmask [0:1],
  input logic [63:0] cpu_req_wdata [0:1],
  output logic cpu_resp_valid [0:1],
  input logic cpu_resp_ready [0:1],
  output logic [31:0] cpu_resp_addr [0:1],
  output logic cpu_resp_write [0:1],
  output logic [63:0] cpu_resp_rdata [0:1],
  output logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1],
  output logic cluster_cpu_req_valid [0:1],
  input logic cluster_cpu_req_ready [0:1],
  input logic cluster_cpu_resp_valid [0:1],
  output logic cluster_cpu_resp_ready [0:1],
  input logic [31:0] cluster_cpu_resp_addr [0:1],
  input logic cluster_cpu_resp_write [0:1],
  input logic [63:0] cluster_cpu_resp_rdata [0:1],
  input logic [TXN_ID_WIDTH-1:0] cluster_cpu_resp_txn_id [0:1],
  output logic mmio_req_valid,
  input logic mmio_req_ready,
  output logic [31:0] mmio_req_addr,
  output logic [2:0] mmio_req_size,
  output logic mmio_req_write,
  output logic [7:0] mmio_req_wmask,
  output logic [63:0] mmio_req_wdata,
  input logic mmio_resp_valid,
  output logic mmio_resp_ready,
  input logic [63:0] mmio_resp_rdata,
  output logic cpu_req_is_mmio [0:1],
  output logic protocol_error
);
  typedef enum logic [1:0] {MMIO_IDLE, MMIO_SEND_REQ, MMIO_WAIT_RESP} mmio_state_t;
  mmio_state_t mmio_state_q;
  logic [1:0] mmio_candidates;
  logic mmio_select_core;
  logic mmio_accept;
  logic mmio_owner_pending;
  logic mmio_resp_to_core [0:1];
  logic [TXN_ID_WIDTH-1:0] mmio_txn_counter_q;
  logic [TXN_ID_WIDTH-1:0] mmio_txn_q;
  logic [31:0] mmio_addr_q;
  logic mmio_write_q;
  logic [7:0] mmio_wmask_q;
  logic [63:0] mmio_wdata_q;
  logic mmio_owner_q;
  logic mmio_prefer_core1_q;

  assign mmio_owner_pending = (mmio_state_q != MMIO_IDLE);

  always_comb begin
    for (integer core = 0; core < 2; core = core + 1) begin
      cpu_req_is_mmio[core] = (cpu_req_addr[core] >= 32'h3000_0000) &&
                              (cpu_req_addr[core] <  32'h8000_0000);
      cluster_cpu_req_valid[core] = cpu_req_valid[core] &&
                                    !cpu_req_is_mmio[core] &&
                                    !fatal_error &&
                                    !(mmio_owner_pending &&
                                      (mmio_owner_q == 1'(core)));
      cluster_cpu_resp_ready[core] = cpu_resp_ready[core] &&
                                     !fatal_error &&
                                     !(mmio_owner_pending &&
                                       (mmio_owner_q == 1'(core)));
      mmio_candidates[core] = cpu_req_valid[core] &&
                              cpu_req_is_mmio[core] &&
                              !reset && !fatal_error &&
                              cluster_cpu_req_ready[core] &&
                              !(mmio_owner_pending &&
                                (mmio_owner_q == 1'(core)));
    end

    if (mmio_candidates[0] && mmio_candidates[1])
      mmio_select_core = mmio_prefer_core1_q;
    else
      mmio_select_core = mmio_candidates[1];
    mmio_accept = (mmio_state_q == MMIO_IDLE) &&
                  mmio_candidates[mmio_select_core];

    for (integer core = 0; core < 2; core = core + 1) begin
      cpu_req_ready[core] = !reset && !fatal_error && (cpu_req_is_mmio[core] ?
        (mmio_accept && (mmio_select_core == 1'(core))) :
        (cluster_cpu_req_ready[core] &&
         !(mmio_owner_pending && (mmio_owner_q == 1'(core)))));
      mmio_resp_to_core[core] = (mmio_state_q == MMIO_WAIT_RESP) &&
                                mmio_resp_valid &&
                                (mmio_owner_q == 1'(core));
      cpu_resp_valid[core] = !reset && !fatal_error &&
                             (cluster_cpu_resp_valid[core] ||
                              mmio_resp_to_core[core]);
      cpu_resp_addr[core] = (mmio_owner_pending &&
                             (mmio_owner_q == 1'(core))) ?
                            mmio_addr_q : cluster_cpu_resp_addr[core];
      cpu_resp_write[core] = (mmio_owner_pending &&
                              (mmio_owner_q == 1'(core))) ?
                             mmio_write_q : cluster_cpu_resp_write[core];
      cpu_resp_rdata[core] = mmio_resp_to_core[core] ?
                             mmio_resp_rdata : cluster_cpu_resp_rdata[core];
      cpu_resp_txn_id[core] = (mmio_owner_pending &&
                               (mmio_owner_q == 1'(core))) ?
                              mmio_txn_q : cluster_cpu_resp_txn_id[core];
    end

    mmio_req_valid = !reset && !fatal_error &&
                     (mmio_state_q == MMIO_SEND_REQ);
    mmio_req_addr = mmio_addr_q;
    mmio_req_size = 3'b011;
    mmio_req_write = mmio_write_q;
    mmio_req_wmask = mmio_wmask_q;
    mmio_req_wdata = mmio_wdata_q;
    mmio_resp_ready = !reset && !fatal_error &&
                      (mmio_state_q == MMIO_WAIT_RESP) &&
                      cpu_resp_ready[mmio_owner_q];
  end

  always_ff @(posedge clock) begin
    if (reset) begin
      mmio_state_q <= MMIO_IDLE;
      mmio_txn_counter_q <= '0;
      mmio_txn_q <= '0;
      mmio_addr_q <= '0;
      mmio_write_q <= 1'b0;
      mmio_wmask_q <= '0;
      mmio_wdata_q <= '0;
      mmio_owner_q <= 1'b0;
      mmio_prefer_core1_q <= 1'b0;
      protocol_error <= 1'b0;
    end else begin
      if (mmio_resp_valid && (mmio_state_q != MMIO_WAIT_RESP))
        protocol_error <= 1'b1;
      case (mmio_state_q)
        MMIO_IDLE: begin
          if (mmio_accept) begin
            mmio_owner_q <= mmio_select_core;
            mmio_txn_q <= mmio_txn_counter_q;
            mmio_txn_counter_q <= mmio_txn_counter_q + 1'b1;
            mmio_addr_q <= cpu_req_addr[mmio_select_core];
            mmio_write_q <= cpu_req_write[mmio_select_core];
            mmio_wmask_q <= cpu_req_wmask[mmio_select_core];
            mmio_wdata_q <= cpu_req_wdata[mmio_select_core];
            mmio_state_q <= MMIO_SEND_REQ;
          end
        end
        MMIO_SEND_REQ: begin
          if (mmio_req_valid && mmio_req_ready)
            mmio_state_q <= MMIO_WAIT_RESP;
        end
        MMIO_WAIT_RESP: begin
          if (mmio_resp_valid && mmio_resp_ready) begin
            mmio_prefer_core1_q <= ~mmio_owner_q;
            mmio_state_q <= MMIO_IDLE;
          end
        end
        default: begin
          protocol_error <= 1'b1;
          mmio_state_q <= MMIO_IDLE;
        end
      endcase
    end
  end
endmodule
