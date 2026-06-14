require "rails_helper"

# The external Appendix A contract: bearer auth, structured booking in, wrapped
# estimate out, and the exact error shapes HouseAccount's partner endpoints use.
RSpec.describe "POST /pricing-estimate", type: :request do
  let(:secret) { "test-secret" }
  let(:auth_headers) do
    { "Authorization" => "Bearer #{secret}", "Content-Type" => "application/json" }
  end
  let(:valid_body) do
    {
      job_id: "abc123", service_category: "Plumbing", zip_code: "78704",
      job_description: "Replace 50-gallon gas water heater"
    }
  end
  let(:model_estimate) do
    {
      "job_id" => "abc123", "estimate_lo" => 1450.0, "estimate_hi" => 2200.0,
      "estimate_midpoint" => 1825.0, "confidence" => 0.78,
      "model_version" => "houseaccount-pricing-v1.0.0"
    }
  end

  before do
    ENV["GAUNTLET_PRICING_SECRET"] = secret
    allow(ModelServiceClient).to receive(:predict).and_return(model_estimate)
  end

  it "returns the wrapped estimate on success" do
    post "/pricing-estimate", params: valid_body.to_json, headers: auth_headers

    expect(response).to have_http_status :ok
    body = response.parsed_body
    expect(body).to include(
      "ok" => true, "job_id" => "abc123", "estimate_lo" => 1450.0,
      "estimate_hi" => 2200.0, "estimate_midpoint" => 1825.0,
      "confidence" => 0.78, "model_version" => "houseaccount-pricing-v1.0.0"
    )
    expect(body["estimate_lo"]).to be <= body["estimate_midpoint"]
  end

  it "rejects a missing bearer token" do
    post "/pricing-estimate", params: valid_body.to_json,
                              headers: { "Content-Type" => "application/json" }

    expect(response).to have_http_status :unauthorized
    expect(response.parsed_body).to eq("error" => "Unauthorized")
  end

  it "rejects a wrong bearer token" do
    post "/pricing-estimate", params: valid_body.to_json,
                              headers: auth_headers.merge("Authorization" => "Bearer wrong")

    expect(response).to have_http_status :unauthorized
  end

  it "requires the job_description field" do
    post "/pricing-estimate", params: valid_body.except(:job_description).to_json,
                              headers: auth_headers

    expect(response).to have_http_status :bad_request
    expect(response.parsed_body).to eq("error" => "job_description required")
  end

  it "rejects malformed JSON" do
    post "/pricing-estimate", params: "{ not valid json", headers: auth_headers

    expect(response).to have_http_status :bad_request
    expect(response.parsed_body).to eq("error" => "Malformed JSON")
  end

  it "returns 405 for a non-POST method" do
    get "/pricing-estimate", headers: auth_headers

    expect(response).to have_http_status :method_not_allowed
    expect(response.parsed_body).to eq("error" => "Method not allowed")
  end
end
