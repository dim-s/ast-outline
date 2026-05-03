<?php

namespace App;

use App\Models\{User, Post as BlogPost, Comment};
use function App\Helpers\{render, escape as e};
use const App\Config\{DEFAULT_LIMIT, MAX_RETRIES};
use App\{
    Service\Mailer,
    Service\Cache as CacheService
};

class Foo {}
