// NestJS-style fixture: decorators on class and methods.
// (Legal TypeScript regardless of whether Nest is present.)
function Controller(path: string): ClassDecorator {
    return () => {};
}
function Get(path?: string): MethodDecorator {
    return () => {};
}
function Post(path?: string): MethodDecorator {
    return () => {};
}

@Controller("/users")
export class UserController {
    @Get()
    findAll(): string {
        return "all";
    }

    @Get(":id")
    findOne(id: string): string {
        return id;
    }

    @Post()
    create(body: { name: string }): { id: string } {
        return { id: "1" };
    }
}
