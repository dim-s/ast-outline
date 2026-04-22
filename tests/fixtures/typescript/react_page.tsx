// React / Next.js-style page. Exercises:
//   - TSX parser path
//   - interface declarations
//   - `export async function` (metadata / static params helpers)
//   - `export default function` component
//   - arrow-function component assigned to const
//   - JSDoc block before a function
import type { Metadata } from "next";

interface PageProps {
    params: { slug: string[] };
}

export const dynamicParams = true;

export async function generateStaticParams(): Promise<Array<{ slug: string[] }>> {
    return [];
}

/**
 * Generate metadata for SEO + social sharing.
 */
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    return { title: params.slug.join("/") };
}

// A plain helper used by the page
function wrapBody(content: string): string {
    return `<div>${content}</div>`;
}

// Arrow component, exported via `export const`
export const Sidebar = ({ items }: { items: string[] }): JSX.Element => {
    return <aside>{items.join(", ")}</aside>;
};

export default function Page({ params }: PageProps): JSX.Element {
    const body = wrapBody(params.slug.join("/"));
    return <main dangerouslySetInnerHTML={{ __html: body }} />;
}
