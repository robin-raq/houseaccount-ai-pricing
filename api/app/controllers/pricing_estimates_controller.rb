# Implements the Appendix A contract: bearer auth, required-field validation,
# delegation to the model service, and the wrapped { ok: true, ... } response.
class PricingEstimatesController < ApplicationController
  include Priceable

  before_action :authenticate_bearer!

  def create
    missing = blank_required_field
    return render_error "#{missing} required", :bad_request if missing

    estimate = ModelServiceClient.predict booking_payload
    render json: success_body(estimate)
  end

private

  def success_body(estimate)
    {
      ok: true,
      job_id: estimate.fetch("job_id"),
      estimate_lo: estimate.fetch("estimate_lo"),
      estimate_hi: estimate.fetch("estimate_hi"),
      estimate_midpoint: estimate.fetch("estimate_midpoint"),
      confidence: estimate.fetch("confidence"),
      model_version: estimate.fetch("model_version")
    }
  end
end
