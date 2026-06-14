# Public playground used by the demo UI: no bearer, returns the richer estimate
# (scope + OOD reasons), fires the best-effort staging post, and keeps a recent log.
module Demo
  class EstimatesController < ApplicationController
    include Priceable

    rescue_from ModelServiceClient::Error, with: :upstream_unavailable

    def create
      error = booking_error
      return render_error error, :bad_request if error

      payload = booking_payload
      estimate = ModelServiceClient.predict payload
      staging_status = StagingClient.post_estimate payload, estimate
      RequestLog.record log_entry(payload, estimate, staging_status)
      render json: demo_body(estimate, staging_status)
    end

    def index
      render json: { estimates: RequestLog.recent }
    end

  private

    def demo_body(estimate, staging_status)
      {
        ok: true,
        job_id: estimate["job_id"],
        estimate_lo: estimate["estimate_lo"],
        estimate_hi: estimate["estimate_hi"],
        estimate_midpoint: estimate["estimate_midpoint"],
        confidence: estimate["confidence"],
        model_version: estimate["model_version"],
        scope: estimate["scope"],
        ood_reasons: estimate["ood_reasons"],
        latency_ms: estimate["latency_ms"],
        staging_status: staging_status
      }
    end

    def log_entry(payload, estimate, staging_status)
      {
        job_id: estimate["job_id"],
        service_category: payload["service_category"],
        estimate_midpoint: estimate["estimate_midpoint"],
        confidence: estimate["confidence"],
        latency_ms: estimate["latency_ms"],
        staging_status: staging_status
      }
    end
  end
end
