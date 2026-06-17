package com.example.integrationsuiteagent.tool;

import dev.langchain4j.agent.tool.Tool;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class CommunicationTools {

    public record CommunicationArrangementDto(String systemId, String scenarioId, String name, List<String> inboundServices) {
    }

    public record InboundServiceUrlResult(String systemId, String scenarioId, String serviceName, String url, String authHint) {
    }

    public record CredentialValidationResult(String tenantId, String credentialAlias, boolean valid, String message) {
    }

    @Tool("List SAP S/4HANA communication arrangements known to the platform")
    public List<CommunicationArrangementDto> listCommunicationArrangements(String systemId) {
        return List.of(new CommunicationArrangementDto(systemId, "SAP_COM_0053", "Purchase Order Integration", List.of("API_PURCHASEORDER_2")));
    }

    @Tool("Get inbound service URL by communication scenario and OData service name")
    public InboundServiceUrlResult getInboundServiceUrl(String systemId, String scenarioId, String serviceName) {
        String host = switch (systemId) {
            case "S4_DEV" -> "https://my201498-api.s4hana.sapcloud.cn";
            case "S4_CUSTOMIZING" -> "https://my201496-api.s4hana.sapcloud.cn";
            default -> "https://<api-host>";
        };
        return new InboundServiceUrlResult(
                systemId,
                scenarioId,
                serviceName,
                host + "/sap/opu/odata4/sap/api_purchaseorder_2/srvd_a2x/sap/purchaseorder/0001/",
                "Use Communication User basic auth or OAuth from the communication arrangement; do not store secrets in the graph."
        );
    }

    @Tool("Validate an Integration Suite credential alias without exposing its secret")
    public CredentialValidationResult validateCredentialAlias(String tenantId, String credentialAlias) {
        boolean looksValid = credentialAlias != null && !credentialAlias.isBlank();
        return new CredentialValidationResult(tenantId, credentialAlias, looksValid,
                looksValid ? "Alias format accepted by prototype." : "Credential alias is required.");
    }
}
