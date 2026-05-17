--- Direct-return-table module pattern: no intermediate ``M`` variable.
--- Common in small utility modules and Neovim plugin specs.
return {
    add = function(a, b) return a + b end,
    sub = function(a, b) return a - b end,
    VERSION = "1.0.0",
    -- Metamethod inside a direct-return table is still an operator.
    __call = function(self, x) return x end,
}
