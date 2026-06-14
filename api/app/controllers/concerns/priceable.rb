# Shared booking-input handling for the contract endpoint and the demo playground.
module Priceable
  extend ActiveSupport::Concern

  REQUIRED_FIELDS = %w[job_id service_category zip_code job_description].freeze
  PERMITTED_FIELDS = %i[
    job_id service_category service_subtype zip_code job_description deadline
    booking_month job_status original_estimate original_estimate_lo original_estimate_hi
  ].freeze

  def blank_required_field
    REQUIRED_FIELDS.find { |field| params[field].blank? }
  end

  def booking_payload
    params.permit(*PERMITTED_FIELDS).to_h
  end
end
