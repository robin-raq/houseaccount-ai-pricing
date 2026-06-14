class ApplicationController < ActionController::API
  rescue_from ActionDispatch::Http::Parameters::ParseError, with: :malformed_json

private

  def authenticate_bearer!
    return if valid_bearer?

    render_error "Unauthorized", :unauthorized
  end

  def valid_bearer?
    header = request.authorization.to_s
    return false unless header.start_with? "Bearer "

    presented = header.delete_prefix "Bearer "
    ActiveSupport::SecurityUtils.secure_compare presented, pricing_secret
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
end
