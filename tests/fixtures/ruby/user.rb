# Domain user model — exercises the full Rails-style class shape:
# inheritance, mixins, associations, attrs, visibility, operators,
# constructors, class methods, constants, alias.
require "json"
require_relative "concerns/searchable"

module App
  module Models
    # Rails ActiveRecord-style user.
    class User < ApplicationRecord
      include Comparable
      extend Searchable
      prepend Auditable

      MAX_NAME_LENGTH = 64
      DEFAULT_ROLE = "member"

      # Posts authored by this user.
      has_many :posts
      has_one :profile
      belongs_to :company
      has_and_belongs_to_many :roles

      attr_accessor :name, :email
      attr_reader :id
      attr_writer :token

      # rdoc-style constructor doc.
      # Second line.
      def initialize(name, email)
        @name = name
        @email = email
      end

      def display_name
        "#{@name} <#{@email}>"
      end

      def self.find_by_name(name)
        where(name: name).first
      end

      def self.with_role(role)
        where(role: role)
      end
      private_class_method :with_role

      # Spaceship for ordering by name.
      def <=>(other)
        @name <=> other.name
      end

      def ==(other)
        other.is_a?(User) && other.id == @id
      end

      def [](key)
        attributes[key]
      end

      def []=(key, value)
        attributes[key] = value
      end

      def -@
        deactivated_copy
      end

      # Alias for backward compatibility.
      alias_method :full_name, :display_name
      alias old_to_s display_name

      private

      def secret_key
        ENV["USER_KEY"]
      end

      def hidden
      end

      protected

      def for_subclass_only
      end

      public

      def public_again
      end

      class << self
        def class_method_in_singleton
          "static!"
        end

        attr_accessor :counter
      end
    end
  end
end

# Reopening a stdlib class.
class String
  def shout
    upcase + "!"
  end
end

# Top-level free function.
def configure!
  puts "configured"
end
