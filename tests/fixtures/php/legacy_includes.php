<?php
/**
 * Pre-Composer / WordPress-style bootstrap. Top-level
 * `require_once` is the only PHP file-level dependency mechanism in
 * pre-PSR-4 codebases — without surfacing these the file looks
 * dependency-less to agents.
 */

require_once __DIR__ . "/config.php";
require_once dirname(__FILE__) . "/helpers.php";

include "optional-helpers.php";
include_once "optional-helpers-once.php";

require ABSPATH . WPINC . "/load.php";

class LegacyService
{
    public function load(): void
    {
        // Lazy load — must NOT appear in the file-level imports list.
        require_once __DIR__ . "/runtime-only.php";
    }
}

function plugin_init(): void
{
    // Same: include inside a function body is runtime, not module-level.
    require __DIR__ . "/init-only.php";
}

require_once __DIR__ . "/finalize.php";
