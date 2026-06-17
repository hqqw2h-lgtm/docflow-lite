package com.example.integrationsuiteagent.api;

import com.example.integrationsuiteagent.odata.ODataEntityTypeDto;
import com.example.integrationsuiteagent.odata.ODataMetadataDto;
import com.example.integrationsuiteagent.odata.ODataQueryCommand;
import com.example.integrationsuiteagent.odata.ODataQueryResult;
import com.example.integrationsuiteagent.odata.ODataServiceDto;
import com.example.integrationsuiteagent.tool.CommunicationTools;
import com.example.integrationsuiteagent.tool.KnowledgeTools;
import com.example.integrationsuiteagent.tool.ODataDiscoveryTools;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/discovery")
public class DiscoveryController {

    private final ODataDiscoveryTools oDataTools;
    private final CommunicationTools communicationTools;
    private final KnowledgeTools knowledgeTools;

    public DiscoveryController(ODataDiscoveryTools oDataTools, CommunicationTools communicationTools, KnowledgeTools knowledgeTools) {
        this.oDataTools = oDataTools;
        this.communicationTools = communicationTools;
        this.knowledgeTools = knowledgeTools;
    }

    @GetMapping("/systems/{systemId}/odata-services")
    public List<ODataServiceDto> listODataServices(@PathVariable String systemId) {
        return oDataTools.listODataServices(systemId);
    }

    @GetMapping("/systems/{systemId}/odata-services/{serviceName}/metadata")
    public ODataMetadataDto getMetadata(@PathVariable String systemId, @PathVariable String serviceName) {
        return oDataTools.getODataMetadata(systemId, serviceName);
    }

    @GetMapping("/systems/{systemId}/odata-services/{serviceName}/entities/{entityName}")
    public ODataEntityTypeDto getEntityType(
            @PathVariable String systemId,
            @PathVariable String serviceName,
            @PathVariable String entityName
    ) {
        return oDataTools.getEntityType(systemId, serviceName, entityName);
    }

    @PostMapping("/odata-query")
    public ODataQueryResult queryOData(@RequestBody ODataQueryCommand command) {
        return oDataTools.queryOData(command);
    }

    @GetMapping("/systems/{systemId}/communication-arrangements")
    public List<CommunicationTools.CommunicationArrangementDto> listCommunicationArrangements(@PathVariable String systemId) {
        return communicationTools.listCommunicationArrangements(systemId);
    }

    @GetMapping("/systems/{systemId}/inbound-service-url")
    public CommunicationTools.InboundServiceUrlResult getInboundServiceUrl(
            @PathVariable String systemId,
            @RequestParam String scenarioId,
            @RequestParam String serviceName
    ) {
        return communicationTools.getInboundServiceUrl(systemId, scenarioId, serviceName);
    }

    @GetMapping("/knowledge")
    public List<KnowledgeTools.KnowledgeHit> retrieveKnowledge(@RequestParam String query) {
        return knowledgeTools.retrieveKnowledge(query);
    }
}
