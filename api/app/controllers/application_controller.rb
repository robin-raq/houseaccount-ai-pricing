class ApplicationController < ActionController::API
  rescue_from ActionDispatch::Http::Parameters::ParseError, with: :malformed_json

private

  def authenticate_bearer!
    return if valid_bearer?

    render_error "Unauthorized", :unauthorized
  end

  def valid_bearer?
    return false if pricing_secret.blank? # fail closed on a missing/unset secret

    header = request.authorization.to_s
    return false unless header.start_with? "Bearer "

    presented = header.delete_prefix "Bearer "
    # Hash both sides so the constant-time compare is independent of token length.
    ActiveSupport::SecurityUtils.secure_compare digest(presented), digest(pricing_secret)
  end

  def digest(value)
    Digest::SHA256.hexdigest value
  end

  def pricing_secret
    ENV["GAUNTLET_PRICING_SECRET"].to_s
  end

  def render_error(message, status)
    render json: { error: message }, status: status
  end

  def malformed_json
    render_error "Malformed JSON", :bad_request
  end

  def upstream_unavailable
    render_error "Pricing service unavailable", :service_unavailable
  end
end
