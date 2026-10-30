  import coherence_protocol_pkg::*;

  logic clock = 1'b0;
  logic reset;

  logic cpu_req_valid [0:1];
  logic cpu_req_ready [0:1];
  logic [31:0] cpu_req_addr [0:1];
  logic cpu_req_write [0:1];
  logic [7:0] cpu_req_wmask [0:1];
  logic [63:0] cpu_req_wdata [0:1];
  logic cpu_resp_valid [0:1];
  logic cpu_resp_ready [0:1];
  logic [31:0] cpu_resp_addr [0:1];
  logic cpu_resp_write [0:1];
  logic [63:0] cpu_resp_rdata [0:1];
  logic [TXN_ID_WIDTH-1:0] cpu_resp_txn_id [0:1];
  logic cpu_hit_event [0:1];
  logic cpu_miss_event [0:1];
  logic metadata_commit_valid [0:1];
  logic [31:0] metadata_commit_line_addr [0:1];
  mesi_state_t metadata_commit_state [0:1];
  logic metadata_commit_is_snoop [0:1];
  logic [1:0] metadata_commit_seen = 2'b00;
  logic [5:0] monitor_cpu_state, monitor_snoop_state;
  logic [63:0] monitor_cpu_active_addr;
  logic [7:0] monitor_replace_state;

  logic [1:0] dir_req_ready;
  logic dir_req_valid;
  logic dir_req_ready_from_directory;
  logic dir_req_src_id;
  request_opcode_t dir_req_opcode;
  logic [31:0] dir_req_line_addr;
  logic [TXN_ID_WIDTH-1:0] dir_req_txn_id;

  logic put_xfer_start [0:1];
  logic [31:0] put_xfer_addr [0:1];
  logic [TXN_ID_WIDTH-1:0] put_xfer_txn_id [0:1];
  logic put_data_valid [0:1];
  logic put_data_ready [0:1];
  logic [2:0] put_data_beat_idx [0:1];
  logic [63:0] put_data [0:1];
  logic put_data_last [0:1];

  logic grant_valid [0:1];
  logic [1:0] grant_valid_drive;
  logic grant_ready [0:1];
  grant_opcode_t grant_opcode [0:1];
  logic [5:0] grant_opcode_drive;
  logic [TXN_ID_WIDTH-1:0] grant_txn_id [0:1];
  logic [2*TXN_ID_WIDTH-1:0] grant_txn_id_drive;
  logic grant_data_valid [0:1];
  logic [1:0] grant_data_valid_drive;
  logic grant_data_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_data_txn_id [0:1];
  logic [2*TXN_ID_WIDTH-1:0] grant_data_txn_id_drive;
  logic [2:0] grant_data_beat_idx [0:1];
  logic [5:0] grant_data_beat_idx_drive;
  logic [63:0] grant_data [0:1];
  logic [127:0] grant_data_drive;
  logic grant_data_last [0:1];
  logic [1:0] grant_data_last_drive;
  logic grant_commit_valid [0:1];
  logic grant_commit_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] grant_commit_txn_id [0:1];

  logic snoop_valid [0:1];
  logic snoop_ready [0:1];
  logic [31:0] snoop_line_addr [0:1];
  snoop_opcode_t snoop_opcode [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_txn_id [0:1];
  logic snoop_rsp_valid [0:1];
  logic snoop_rsp_ready [0:1];
  snoop_response_t snoop_rsp_opcode [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_rsp_txn_id [0:1];
  logic snoop_rsp_has_data [0:1];
  logic snoop_data_valid [0:1];
  logic snoop_data_ready [0:1];
  logic [TXN_ID_WIDTH-1:0] snoop_data_txn_id [0:1];
  logic [2:0] snoop_data_beat_idx [0:1];
  logic [63:0] snoop_data [0:1];
  logic snoop_data_last [0:1];

  logic replace_valid [0:1];
  logic [1:0] replace_way [0:1];
  mesi_state_t replace_state [0:1];
  logic [31:0] replace_line_addr [0:1];
  logic [1:0] controller_protocol_error;
  logic [1:0] array_protocol_error;

  always #5 clock = ~clock;

  always @(posedge clock) begin
    if (!reset) begin
      for (integer core_id = 0; core_id < 2; core_id++) begin
        if (metadata_commit_valid[core_id]) begin
          if (metadata_commit_line_addr[core_id][5:0] != 6'b0 ||
              metadata_commit_state[core_id] != MESI_E || metadata_commit_is_snoop[core_id])
            $fatal(1, "unexpected refill metadata commit core=%0d addr=%08x state=%0d snoop=%b",
                   core_id, metadata_commit_line_addr[core_id],
                   metadata_commit_state[core_id], metadata_commit_is_snoop[core_id]);
          metadata_commit_seen[core_id] <= 1'b1;
        end
      end
    end
  end

  always_comb begin
    grant_valid[0] = grant_valid_drive[0];
    grant_valid[1] = grant_valid_drive[1];
    grant_opcode[0] = grant_opcode_t'(grant_opcode_drive[2:0]);
    grant_opcode[1] = grant_opcode_t'(grant_opcode_drive[5:3]);
    grant_txn_id[0] = grant_txn_id_drive[TXN_ID_WIDTH-1:0];
    grant_txn_id[1] = grant_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH];
    grant_data_valid[0] = grant_data_valid_drive[0];
    grant_data_valid[1] = grant_data_valid_drive[1];
    grant_data_txn_id[0] = grant_data_txn_id_drive[TXN_ID_WIDTH-1:0];
    grant_data_txn_id[1] = grant_data_txn_id_drive[2*TXN_ID_WIDTH-1:TXN_ID_WIDTH];
    grant_data_beat_idx[0] = grant_data_beat_idx_drive[2:0];
    grant_data_beat_idx[1] = grant_data_beat_idx_drive[5:3];
    grant_data[0] = grant_data_drive[63:0];
    grant_data[1] = grant_data_drive[127:64];
    grant_data_last[0] = grant_data_last_drive[0];
    grant_data_last[1] = grant_data_last_drive[1];
  end

  DualL1MesiCluster dut (.*);
