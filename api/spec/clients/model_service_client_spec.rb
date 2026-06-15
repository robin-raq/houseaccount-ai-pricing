require "rails_helper"

# The client is the seam between Rails and the model service: every bad upstream
# response must surface as ModelServiceClient::Error (which controllers turn into a
# controlled 503), never an unhandled exception that would 500.
RSpec.describe ModelServiceClient do
  def stub_response(code, body)
    response = instance_double(Net::HTTPResponse, code: code, body: body)
    allow_any_instance_of(described_class).to receive(:request_json).and_return(response)
  end

  let(:complete) do
    {
      job_id: "x", estimate_lo: 100, estimate_hi: 200, estimate_midpoint: 150,
      confidence: 0.8, model_version: "v1"
    }
  end

  it "returns the parsed estimate when the response is complete" do
    stub_response "200", complete.to_json
    expect(described_class.predict({})).to include("estimate_midpoint" => 150)
  end

  it "raises Error on a non-200 response" do
    stub_response "500", ""
    expect { described_class.predict({}) }.to raise_error(described_class::Error)
  end

  it "raises Error on a 200 with malformed JSON" do
    stub_response "200", "{ not json"
    expect { described_class.predict({}) }.to raise_error(described_class::Error, /malformed/)
  end

  it "raises Error when a required key is missing from a 200" do
    stub_response "200", { job_id: "x", estimate_lo: 100 }.to_json
    expect { described_class.predict({}) }.to raise_error(described_class::Error, /omitted/)
  end
end
