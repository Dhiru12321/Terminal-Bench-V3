#include "harness/runner.h"
#include "harness/trace.h"
#include "game/world.h"
#include "net/session.h"
#include "replay/codec_ops.h"
#include "replay/io.h"
#include "replay/version.h"
#include "sim/tick_driver.h"
#include "util/digest.h"
#include "util/json_scan.h"

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace harness {

static std::string read_all(const std::string& path) {
  std::ifstream f(path);
  if (!f) {
    throw std::runtime_error("read pack");
  }
  return std::string(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
}

static std::vector<std::array<std::int8_t, 2>> load_commands(const util::JsonValue& sc, int ticks) {
  const auto& cmd_arr = sc.obj.at("commands").arr;
  if (static_cast<int>(cmd_arr.size()) != ticks) {
    throw std::runtime_error("commands length");
  }
  std::vector<std::array<std::int8_t, 2>> out;
  out.reserve(static_cast<std::size_t>(ticks));
  for (const auto& row : cmd_arr) {
    const std::int8_t a = static_cast<std::int8_t>(static_cast<int>(row.arr.at(0).num));
    const std::int8_t b = static_cast<std::int8_t>(static_cast<int>(row.arr.at(1).num));
    out.push_back({a, b});
  }
  return out;
}

static std::vector<std::uint8_t> load_masks(const util::JsonValue& sc, int ticks) {
  const auto it = sc.obj.find("masks");
  if (it == sc.obj.end()) {
    return std::vector<std::uint8_t>(static_cast<std::size_t>(ticks), 3);
  }
  const auto& arr = it->second.arr;
  if (static_cast<int>(arr.size()) != ticks) {
    throw std::runtime_error("masks length");
  }
  std::vector<std::uint8_t> out;
  out.reserve(arr.size());
  for (const auto& m : arr) {
    out.push_back(static_cast<std::uint8_t>(static_cast<int>(m.num)));
  }
  return out;
}

static sim::TickInputs make_tick_input(eng::Tick tick, const std::array<std::int8_t, 2>& dx,
                                       std::uint8_t mask) {
  sim::TickInputs tin{};
  tin.tick = tick;
  tin.staged[0].dx = dx[0];
  tin.staged[1].dx = dx[1];
  tin.remote_slot_present[0] = (mask & 1u) != 0;
  tin.remote_slot_present[1] = (mask & 2u) != 0;
  return tin;
}

static std::vector<replay::PayloadRow> make_payload_rows(const std::vector<std::array<std::int8_t, 2>>& cmds,
                                                         const std::vector<std::uint8_t>& masks) {
  std::vector<replay::PayloadRow> rows;
  rows.reserve(cmds.size());
  for (std::size_t i = 0; i < cmds.size(); ++i) {
    replay::PayloadRow r;
    r.tick = static_cast<eng::Tick>(static_cast<int>(i));
    r.p0 = cmds[i][0];
    r.p1 = cmds[i][1];
    r.mask = masks[i];
    rows.push_back(r);
  }
  return rows;
}

static std::string run_uninterrupted_digest(const std::vector<std::array<std::int8_t, 2>>& cmds,
                                            const std::vector<std::uint8_t>& masks, std::uint64_t seed,
                                            sim::TickDriver& driver, game::World& world,
                                            std::vector<harness::TraceBundleLine>* trace_out,
                                            const std::string& trace_id) {
  driver.reset(seed);
  world.reset();
  const int ticks = static_cast<int>(cmds.size());
  for (int t = 0; t < ticks; ++t) {
    const auto tin = make_tick_input(static_cast<eng::Tick>(t), cmds[t], masks[static_cast<std::size_t>(t)]);
    driver.run_tick(static_cast<eng::Tick>(t), tin, world);
  }
  if (trace_out != nullptr) {
    for (const auto& row : driver.log().rows()) {
      trace_out->emplace_back(trace_id, row);
    }
  }
  const eng::Tick last_tick = static_cast<eng::Tick>(ticks - 1);
  return util::digest_hex_256(world.canon_at(last_tick));
}

static std::string tail_proj(sim::TickDriver& driver, std::size_t n) {
  return driver.log().tail_projection(n);
}

int run_matrix(const std::string& pack_path, const std::string& out_dir) {
  const std::string raw = read_all(pack_path);
  const util::JsonValue root = util::parse_json(raw);
  if (root.kind != util::JsonValue::Kind::Object) {
    std::cerr << "bad pack root\n";
    return 2;
  }
  const auto* scenarios_node = root.get("scenarios");
  if (scenarios_node == nullptr || scenarios_node->kind != util::JsonValue::Kind::Array) {
    std::cerr << "missing scenarios\n";
    return 2;
  }

  std::filesystem::create_directories(out_dir);
  std::ostringstream report;
  report << "{\"schema_version\":4,\"replay_format_revision\":" << replay::writer_current_revision()
         << ",\"scenarios\":{";

  std::vector<harness::TraceBundleLine> trace_lines;
  std::uint64_t rng_world_sum = 0;
  std::uint64_t rng_net_sum = 0;

  bool first = true;
  for (const auto& sc : scenarios_node->arr) {
    if (sc.kind != util::JsonValue::Kind::Object) {
      continue;
    }
    const std::string id = sc.obj.at("id").s;
    const std::string mode = sc.obj.at("mode").s;
    const std::uint64_t seed = static_cast<std::uint64_t>(sc.obj.at("seed").num);
    const int ticks = static_cast<int>(sc.obj.at("ticks").num);
    const auto cmds = load_commands(sc, ticks);
    const auto masks = load_masks(sc, ticks);

    game::World world{};
    sim::TickDriver driver{};

    if (!first) {
      report << ',';
    }
    first = false;
    report << "\"" << id << "\":{\"mode\":\"" << mode << "\"";

    if (mode == "duplicate") {
      const std::string d1 =
          run_uninterrupted_digest(cmds, masks, seed, driver, world, &trace_lines, id);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      const std::string d2 =
          run_uninterrupted_digest(cmds, masks, seed, driver, world, nullptr, id);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      const bool match = (d1 == d2);
      report << ",\"state_digest_hex\":\"" << d1 << "\",\"tail_projection\":\"" << tail_proj(driver, 5)
             << "\",\"straight_run_a\":\"" << d1 << "\",\"straight_run_b\":\"" << d2
             << "\",\"duplicate_match\":" << (match ? "true" : "false") << "}";
    } else if (mode == "reconnect") {
      const int reconnect_after = static_cast<int>(sc.obj.at("reconnect_after").num);
      driver.reset(seed);
      world.reset();
      net::Session session{};
      session.reset(seed);
      for (int t = 0; t < reconnect_after; ++t) {
        const auto tin =
            make_tick_input(static_cast<eng::Tick>(t), cmds[static_cast<std::size_t>(t)],
                            masks[static_cast<std::size_t>(t)]);
        driver.run_tick(static_cast<eng::Tick>(t), tin, world);
      }
      for (int t = reconnect_after; t < ticks; ++t) {
        net::FramedTick ft{};
        ft.tick = static_cast<eng::Tick>(t);
        ft.p0 = cmds[static_cast<std::size_t>(t)][0];
        ft.p1 = cmds[static_cast<std::size_t>(t)][1];
        ft.presence = masks[static_cast<std::size_t>(t)];
        session.push_remote_frame(ft);
      }
      session.catch_up_from_queue(static_cast<eng::Tick>(ticks - 1), driver, world);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      for (const auto& row : driver.log().rows()) {
        trace_lines.emplace_back(id, row);
      }
      const std::string digest =
          util::digest_hex_256(world.canon_at(static_cast<eng::Tick>(ticks - 1)));
      report << ",\"state_digest_hex\":\"" << digest << "\",\"tail_projection\":\"" << tail_proj(driver, 6)
             << "\"}";
    } else if (mode == "replay_roundtrip") {
      const std::string ref = run_uninterrupted_digest(cmds, masks, seed, driver, world, &trace_lines, id);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      const auto rows = make_payload_rows(cmds, masks);
      const auto blob = replay::encode_replay_blob(seed, replay::writer_current_revision(), rows);
      const auto parsed = replay::parse_replay_bytes(
          std::string_view(reinterpret_cast<const char*>(blob.data()), blob.size()));
      const auto dec_rows = replay::decode_rows(parsed.format_revision, parsed.payload);
      const auto inputs = replay::rows_to_inputs(dec_rows);
      driver.reset(seed);
      world.reset();
      for (const auto& tin : inputs) {
        driver.run_tick(tin.tick, tin, world);
      }
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      const std::string rt =
          util::digest_hex_256(world.canon_at(static_cast<eng::Tick>(ticks - 1)));
      report << ",\"state_digest_hex\":\"" << ref << "\",\"roundtrip_digest\":\"" << rt
             << "\",\"roundtrip_match\":" << ((ref == rt) ? "true" : "false")
             << ",\"tail_projection\":\"" << tail_proj(driver, 5) << "\"}";
    } else if (mode == "resume") {
      const int resume_from = static_cast<int>(sc.obj.at("resume_from_tick").num);
      const std::string ref = run_uninterrupted_digest(cmds, masks, seed, driver, world, nullptr, id);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      const auto rows = make_payload_rows(cmds, masks);
      const auto blob = replay::encode_replay_blob(seed, replay::writer_current_revision(), rows);
      const auto parsed = replay::parse_replay_bytes(
          std::string_view(reinterpret_cast<const char*>(blob.data()), blob.size()));
      const auto dec_rows = replay::decode_rows(parsed.format_revision, parsed.payload);
      const auto sliced = replay::slice_rows_from_tick(dec_rows, static_cast<eng::Tick>(resume_from));
      const auto inputs = replay::rows_to_inputs(sliced);
      driver.reset(seed);
      world.reset();
      for (int t = 0; t < resume_from; ++t) {
        const auto tin =
            make_tick_input(static_cast<eng::Tick>(t), cmds[static_cast<std::size_t>(t)],
                            masks[static_cast<std::size_t>(t)]);
        driver.run_tick(static_cast<eng::Tick>(t), tin, world);
      }
      for (const auto& tin : inputs) {
        driver.run_tick(tin.tick, tin, world);
      }
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      for (const auto& row : driver.log().rows()) {
        trace_lines.emplace_back(id, row);
      }
      const std::string tail = util::digest_hex_256(world.canon_at(static_cast<eng::Tick>(ticks - 1)));
      report << ",\"baseline_digest_hex\":\"" << ref << "\",\"state_digest_hex\":\"" << tail
             << "\",\"resume_ok\":" << ((ref == tail) ? "true" : "false") << ",\"tail_projection\":\""
             << tail_proj(driver, 5) << "\"}";
    } else if (mode == "rollback_burst") {
      const std::string digest =
          run_uninterrupted_digest(cmds, masks, seed, driver, world, &trace_lines, id);
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      report << ",\"state_digest_hex\":\"" << digest << "\",\"tail_projection\":\"" << tail_proj(driver, 7)
             << "\"}";
    } else if (mode == "legacy_blob") {
      const auto rows = make_payload_rows(cmds, masks);
      const auto blob = replay::encode_replay_blob_revision1(seed, rows);
      const std::string tmp = out_dir + "/_internal_legacy.rlbd";
      replay::write_blob_file(tmp, blob);
      const auto rawb = replay::read_blob_file(tmp);
      const auto parsed = replay::parse_replay_bytes(
          std::string_view(reinterpret_cast<const char*>(rawb.data()), rawb.size()));
      const auto dec_rows = replay::decode_rows(parsed.format_revision, parsed.payload);
      const auto inputs = replay::rows_to_inputs(dec_rows);
      driver.reset(seed);
      world.reset();
      for (const auto& tin : inputs) {
        driver.run_tick(tin.tick, tin, world);
      }
      rng_world_sum += driver.rng().world.total_draws();
      rng_net_sum += driver.rng().net.total_draws();
      for (const auto& row : driver.log().rows()) {
        trace_lines.emplace_back(id, row);
      }
      const std::string digest =
          util::digest_hex_256(world.canon_at(static_cast<eng::Tick>(ticks - 1)));
      report << ",\"state_digest_hex\":\"" << digest << "\",\"tail_projection\":\"" << tail_proj(driver, 4)
             << "\",\"legacy_revision_read\":" << parsed.format_revision << "}";
    } else {
      report << ",\"error\":\"unknown mode\"}";
    }
  }

  report << "},\"rng_channel_totals\":{\"world\":" << rng_world_sum << ",\"net\":" << rng_net_sum << "}";
  report << ",\"reader_lowest_revision\":" << replay::reader_accepts_lowest_revision() << "}";

  const std::string report_path = out_dir + "/matrix_report.json";
  {
    std::ofstream rf(report_path, std::ios::trunc);
    rf << report.str();
  }

  const std::string trace_path = out_dir + "/trace_bundle.jsonl";
  harness::write_trace_bundle(trace_path, trace_lines);

  return 0;
}

}  // namespace harness
