# Edge cases: complex method signatures, heredocs, blocks, conditional
# requires, top-level constants and a top-level method.

require "json"

# Conditional require — top-level `if` is still listed in static imports.
if defined?(Optimist)
  require "optimist"
end

# Conditional require inside a method body — counted as conditional.
def lazy_load_xml
  require "rexml/document"
end

GREETING = <<~MSG
  hello
  world
MSG

# Top-level constant.
MAX_RETRIES = 3

class Mixed
  # method with default args / keyword args / splat / double-splat / block
  def complex(a, b = 1, *rest, c:, d: 2, **opts, &block)
    yield if block_given?
  end

  # method with no parens
  def simple_no_parens
    42
  end

  # method ending with ? (predicate convention)
  def admin?
    @role == "admin"
  end

  # method ending with ! (bang convention — destructive)
  def reset!
    @counter = 0
  end

  # one-line def (Ruby 3.0+)
  def square(x) = x * x
end

# RSpec-style top-level block — should NOT produce a declaration.
RSpec.describe "User" do
  it "is valid" do
    expect(true).to be true
  end
end

# Top-level free function.
def bootstrap(env)
  puts "booting #{env}"
end
