import { type NextRequest, NextResponse } from "next/server";

/**
 * 通用 API 代理路由
 * 将 /api/* 请求转发到后端 FastAPI 服务
 * BACKEND_URL 在运行时读取，Docker 中可配置为 http://backend:8080
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function POST(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function PUT(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(request, await params);
}

/** 代理请求到后端 */
async function proxyRequest(request: NextRequest, params: { path: string[] }) {
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8080";
  const path = params.path.join("/");
  const url = new URL(`/api/${path}`, backendUrl);

  // 保留原始查询参数
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  const headers = new Headers(request.headers);
  headers.delete("host");

  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  // 仅对有 body 的方法传递 body
  if (request.method !== "GET" && request.method !== "HEAD") {
    fetchOptions.body = await request.text();
  }

  try {
    const response = await fetch(url.toString(), fetchOptions);
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json",
      },
    });
  } catch (error) {
    console.error(`代理请求失败: ${url}`, error);
    return NextResponse.json(
      { error: "Backend service unavailable" },
      { status: 502 }
    );
  }
}
