using System.ComponentModel.DataAnnotations;

namespace MATE.Dashboard.Web.Models.Pipeline;

public class MateRunInputModel : IValidatableObject
{
    public string? RunId { get; set; }

    [Required(ErrorMessage = "Module name is required")]
    public string ModuleName { get; set; } = string.Empty;

    [Required(ErrorMessage = "At least one workflow name is required")]
    public string[] WorkflowNames { get; set; } = Array.Empty<string>();

    [Required(ErrorMessage = "At least one converted root is required")]
    public string[] ConvertedRoots { get; set; } = Array.Empty<string>();

    [Required(ErrorMessage = "At least one legacy backend root is required")]
    public string[] LegacyBackendRoots { get; set; } = Array.Empty<string>();

    [Required(ErrorMessage = "At least one legacy frontend root is required")]
    public string[] LegacyFrontendRoots { get; set; } = Array.Empty<string>();

    [Required(ErrorMessage = "Base URL is required")]
    public string BaseUrl { get; set; } = string.Empty;

    [Required(ErrorMessage = "Start URL is required")]
    public string StartUrl { get; set; } = string.Empty;

    [Required(ErrorMessage = "Dotnet test target is required")]
    public string DotnetTestTarget { get; set; } = string.Empty;

    // Optional inputs
    public bool StrictModuleOnly { get; set; } = false;
    public bool StrictAIGeneration { get; set; } = false;
    public bool EnableUserInputPrompting { get; set; } = true;

    public string[] Keywords { get; set; } = Array.Empty<string>();
    public string[] ControllerHints { get; set; } = Array.Empty<string>();
    public string[] ViewHints { get; set; } = Array.Empty<string>();
    public string[] ExpectedEndUrls { get; set; } = Array.Empty<string>();
    public string[] RelatedFolders { get; set; } = Array.Empty<string>();
    public string[] KnownUrls { get; set; } = Array.Empty<string>();

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (string.IsNullOrWhiteSpace(BaseUrl))
        {
            yield break;
        }

        var isValidAbsoluteUri = Uri.TryCreate(BaseUrl.Trim(), UriKind.Absolute, out var parsed)
            && (parsed!.Scheme.Equals(Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase)
                || parsed.Scheme.Equals(Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase));

        if (!isValidAbsoluteUri)
        {
            yield return new ValidationResult(
                "Base URL must be a valid absolute http/https URL (for example http://127.0.0.1:5029).",
                new[] { nameof(BaseUrl) });
        }
    }
}
