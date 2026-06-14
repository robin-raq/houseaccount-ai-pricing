require "rails_helper"

# The public playground the demo UI calls. No bearer (the secret stays server-side);
# returns the richer estimate (scope, OOD reasons) and records a recent-request log.
RSpec.describe "Demo estimates", type: :request do
  let(:json_headers) { { "Content-Type" => "application/json" } }
  let(:booking) do
    { job_id: "d1", service_category: "Cleaning", zip_code: "75062",
      job_description: "Exterior window wash, 2-story, 20 windows" }
  end
  let(:estimate) do
    {
      "job_id" => "d1", "estimate_lo" => 228.0, "estimate_hi" => 306.0,
      "estimate_midpoint" => 264.0, "confidence" => 0.8, "model_version" => "v1",
      "scope" => { "complexity" => "low" }, "ood_reasons" => [], "latency_ms" => 42
    }
  end

  before { allow(ModelServiceClient).to receive(:predict).and_return(estimate) }

  it "prices a booking without requiring a bearer token" do
    post "/demo/estimates", params: booking.to_json, headers: json_headers

    expect(response).to have_http_status :ok
    body = response.parsed_body
    expect(body).to include("ok" => true, "estimate_midpoint" => 264.0, "confidence" => 0.8)
    expect(body["scope"]).to include("complexity" => "low")
    expect(body).to have_key("staging_status")
  end

  it "records the booking in the recent-request log" do
    post "/demo/estimates", params: booking.to_json, headers: json_headers
    get "/demo/estimates"

    expect(response).to have_http_status :ok
    expect(response.parsed_body["estimates"].first).to include("job_id" => "d1")
  end

  it "still validates required fields" do
    post "/demo/estimates", params: { job_id: "x" }.to_json, headers: json_headers

    expect(response).to have_http_status :bad_request
    expect(response.parsed_body).to eq("error" => "service_category required")
  end
end
