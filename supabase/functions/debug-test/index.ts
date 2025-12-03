// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// Extremely simple test to verify Edge Function execution
Deno.serve(async (req) => {
  // Immediate console output
  console.log("🚀 DEBUG: Function started");
  console.error("⚠️ DEBUG: Error log test");
  
  try {
    console.log("📋 DEBUG: Processing request...");
    console.log(`📝 DEBUG: Method = ${req.method}`);
    console.log(`🔗 DEBUG: URL = ${req.url}`);
    
    // Test basic JSON response
    const response = {
      success: true,
      message: "Debug test completed",
      timestamp: new Date().toISOString(),
      method: req.method,
      url: req.url
    };
    
    console.log("✅ DEBUG: About to return response");
    console.log(`📊 DEBUG: Response = ${JSON.stringify(response)}`);
    
    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }
    });
    
  } catch (error) {
    console.error("💥 DEBUG: Error occurred:", error);
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      }
    });
  }
});

console.log("🔧 DEBUG: Function module loaded");